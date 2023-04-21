import enum
import time

import pyautogui as pag
import utilities.api.item_ids as ids
import utilities.color as clr
import utilities.random_util as rd
from model.osrs.osrs_bot import OSRSBot
from model.runelite_bot import BotStatus
from utilities.api.morg_http_client import MorgHTTPSocket
from utilities.api.status_socket import StatusSocket
from utilities.geometry import Point, RuneLiteObject

class WalkTiles(enum):
    BANK = clr.PINK
    NEAR_BANK = clr.GREEN
    NEAR_GUILD = clr.BLUE
    GUILD = clr.CYAN


class OSRSWine(OSRSBot):
    def __init__(self):
        bot_title = "Wine"
        description = "This bot power-wines wine"
        super().__init__(bot_title=bot_title, description=description)
        self.running_time = 1
        self.take_breaks = False
        # Setup API
        self.api_m = MorgHTTPSocket()
        self.api_s = StatusSocket()

    def create_options(self):
        self.options_builder.add_slider_option("running_time", "How long to run (minutes)?", 1, 500)
        self.options_builder.add_checkbox_option("take_breaks", "Take breaks?", [" "])

    def save_options(self, options: dict):
        for option in options:
            if option == "running_time":
                self.running_time = options[option]
            elif option == "take_breaks":
                self.take_breaks = options[option] != []
            else:
                self.log_msg(f"Unknown option: {option}")
                print("Developer: ensure that the option keys are correct, and that options are being unpacked correctly.")
                self.options_set = False
                return
        self.log_msg(f"Running time: {self.running_time} minutes.")
        self.log_msg(f"Bot will{' ' if self.take_breaks else ' not '}take breaks.")
        self.log_msg("Options set successfully.")
        self.options_set = True

    def main_loop(self):
        self.log_msg("Selecting inventory...")
        self.mouse.move_to(self.win.cp_tabs[3].random_point())
        self.mouse.click()

        self.logs = 0
        failed_searches = 0

        # Main loop
        start_time = time.time()
        end_time = self.running_time * 60
        jug_last = False

        while time.time() - start_time < end_time:
            jugs = self.get_inv_items(ids.JUG_OF_WATER)
            grapes = self.get_inv_items(ids.GRAPES)
            self.log_msg(f'collected {len(jugs)} jugs, collected {len(grapes)} grapes')

            if not self.api_m.get_is_inv_full():
                if jug_last:
                    self.jug_loop()
                    self.grape_loop()
                    jug_last = False
                else:
                    self.grape_loop()
                    self.jug_loop()
                    jug_last = True

                self.hop_world()
                time.sleep(2)
            else:
                self.get_downstairs()
                self.make_wine()

                self.guild_door()
                self.bank_walk(1)
                self.bank_use()
                self.bank_walk(-1)
                self.guild_door()

                self.get_upstairs()

        self.update_progress(1)
        self.__logout("Finished.")

    def get_downstairs(self):
        self.top_stairs_down()
        time.sleep(2)
        self.middle_stairs_action(2)
        time.sleep(2)
    
    def get_upstairs(self):
        self.bottom_stairs_up()
        time.sleep(2)
        self.middle_stairs_action(1)
        time.sleep(2)

    def make_wine(self):
        self.fill_jugs_with_water()
        time.sleep(2)
        self.merge_grapes_with_jug()
        time.sleep(2)

    def attempt_to_click(self, text, contains_word, contains_color, marker_color, end_time=7, offset=(0,0)):
        start_time = time.time()
        while time.time() - start_time < end_time:

            self.log_msg(f'Searching for {text}...')
            # If our mouse isn't hovering over the object, and we can't find another object...
            if not self.mouseover_text(contains=contains_word, color=contains_color) and not self.__move_mouse_to_nearest_marker(marker_color, offset):
                time.sleep(1)
                self.log_msg(f'failed to find {text}...')
                continue

            time.sleep(0.05)
            # Click if the mouseover text assures us we're clicking the object
            if not self.mouseover_text(contains=contains_word, color=contains_color):
                self.log_msg(f'failed to find {text}...')
                continue
            self.log_msg("{text} Clicked")
            self.mouse.click()
            time.sleep(2)
            break

    def bank_walk(self, direction):
        # 1 is towards bank -1 is away from bank
        walking_tiles = [WalkTiles.GUILD, WalkTiles.NEAR_GUILD, WalkTiles.NEAR_BANK, WalkTiles.GUILD]
        for tile_color in walking_tiles[::direction]:
            self.attempt_to_click('Walking', 'Walk', clr.OFF_WHITE, tile_color, 7)


    def guild_door(self):
        self.attempt_to_click('door', 'Open', clr.OFF_WHITE, clr.PURPLE, 7)

    def choose_bank(self):
        """
        Has a small chance to choose the second closest bank to the player.
            Returns: bank rectangle or none if no banks are found
            Args: None
        """
        if banks := self.get_all_tagged_in_rect(self.win.game_view, clr.YELLOW):
            banks = sorted(banks, key=RuneLiteObject.distance_from_rect_center)

            if len(banks) == 1:
                return banks[0]
            if (len(banks) > 1):
                return banks[0] if rd.random_chance(.74) else banks[1]
        else:
            self.log_msg("No banks found, trying to adjust camera...")
            if not self.adjust_camera(clr.YELLOW):
                self.log_msg("No banks found, quitting bot...")
                self.stop()
            return (self.choose_bank())

    def open_bank(self):
        """
        This will bank all logs in the inventory.
        Returns: 
            void
        Args: 
            deposit_slots (int) - Inventory position of each different item to deposit.
        """
        # move mouse one of the closes 2 banks

        bank = self.choose_bank()

        # move mouse to bank and click
        self.mouse.move_to(bank.random_point())

        self.mouse.click()

        wait_time = time.time()
        while not self.is_bank_open():
            # if we waited for 10 seconds, break out of loop
            if time.time() - wait_time > 20:
                self.log_msg("We clicked on the bank but player is not idle after 10 seconds, something is wrong, quitting bot.")
                self.stop()
            time.sleep(self.random_sleep_length(.8, 1.3))
        return
    
    def deposit_items(self, slot_list):
        """
        Clicks once on each unique item. 
        Bank must be open already.
        Deposit "All" must be selected.
        Args:
            slot_list: list of inventory slots to deposit items from
        Returns:
            None/Void
        """
        try_count = 0

        if slot_list == -1:
            self.log_msg("No items to deposit, continuing...")
            return

        if slot_list == 0:   # if theres only one item, it is the first slot
            slot_list = [0]

        # move mouse each slot and click to deposit all
        for slot in slot_list:
            self.mouse.move_to(self.win.inventory_slots[slot].random_point())
            self.mouse.click()

        return

    def bank_use(self):
        self.open_bank()
        time.sleep(1)
        self.deposit_items(self.api_m.get_inv_item_first_indice([ids.JUG_OF_WINE, ids.JUG_OF_BAD_WINE, ids.JUG_OF_BAD_WINE_1992]))
        time.sleep(1)
        pag.hotkey('esc')
        time.sleep(1)


    def get_inv_items(self, item):
        return self.api_m.get_inv_item_indices(item)
        
    def merge_grapes_with_jug(self):
        start_time = time.time()
        end_time = 7
        while time.time() - start_time < end_time:
            indices_jug = self.get_inv_items(ids.JUG_OF_WATER)
            indices_grape = self.get_inv_items(ids.GRAPES)
            self.mouse.move_to(self.win.inventory_slots[indices_jug[0]].random_point())
            self.mouse.click()
            time.sleep(2)
            self.mouse.move_to(self.win.inventory_slots[indices_grape[0]].random_point())
            self.mouse.click()
            time.sleep(2)
            pag.hotkey('space')
            time.sleep(15)

        
    def fill_jugs_with_water(self):
        start_time = time.time()
        end_time = 7
        while time.time() - start_time < end_time:
            indices_jug = self.api_m.get_inv_item_indices(ids.JUG)
            self.mouse.move_to(self.win.inventory_slots[indices_jug[0]].random_point())
            self.mouse.click()
            time.sleep(2)

            # If our mouse isn't hovering over a stairs, and we can't find another stairs...
            if not self.mouseover_text(contains="Sink", color=clr.OFF_CYAN) and not self.__move_mouse_to_nearest_marker(clr.RED):
                time.sleep(1)
                self.log_msg("failed to find sink...")
                continue
            self.mouse.click()

            pag.hotkey('space')
            time.sleep(17)


    def top_stairs_down(self):
        self.attempt_to_click('top stairs', 'Climb', clr.OFF_WHITE, clr.CYAN, 7)

    def middle_stairs_action(self, action=1):
        # 1 = up
        # 2 = down
        self.attempt_to_click('middle stairs', 'Climb', clr.OFF_WHITE, clr.BLUE, 7)
        time.sleep(2)
        pag.hotkey(f'{action}')
        time.sleep(2)

    def bottom_stairs_up(self):
        self.attempt_to_click('bottom stairs', 'Climb', clr.OFF_WHITE, clr.YELLOW, 7)

    def hop_world(self):
        if not self.api_m.get_is_inv_full():
            pag.hotkey('ctrlleft', 'shift', 'right')
            time.sleep(1)
            
            pag.hotkey('space')
            time.sleep(0.5)
            pag.hotkey('2')

            time.sleep(7)
            self.log_msg("Selecting inventory...")
            self.mouse.move_to(self.win.cp_tabs[3].random_point())
            self.mouse.click()

    def jug_loop(self): 
        if self.api_m.get_is_inv_full():
            return
        self.attempt_to_click('Jug', 'Jug', clr.OFF_ORANGE, clr.PURPLE, 7, (25, 0))

    def grape_loop(self): 
        if self.api_m.get_is_inv_full():
            return
        self.attempt_to_click('Grapes', 'Grapes', clr.OFF_ORANGE, clr.PINK, 7, (0, -25))


    def __logout(self, msg):
        self.log_msg(msg)
        self.logout()
        self.stop()

    def __move_mouse_to_nearest_marker(self, color: clr.Color, offset: tuple = (0,0), next_nearest=False):
        """
        Locates the nearest table and moves the mouse to it. This code is used multiple times in this script,
        so it's been abstracted into a function.
        Args:
            next_nearest: If True, will move the mouse to the second nearest table. If False, will move the mouse to the
                          nearest table.
            mouseSpeed: The speed at which the mouse will move to the table. See mouse.py for options.
        Returns:
            True if success, False otherwise.
        """
        tables = self.get_all_tagged_in_rect(self.win.game_view, color)
        table = None
        if not tables:
            return False
        # If we are looking for the next nearest table, we need to make sure tables has at least 2 elements
        if next_nearest and len(tables) < 2:
            return False
        tables = sorted(tables, key=RuneLiteObject.distance_from_rect_center)
        table = tables[1] if next_nearest else tables[0]
        if next_nearest:
            rand_point = table.random_point()
            point: Point = Point(rand_point.x + offset[0], rand_point.y + offset[1])
            self.mouse.move_to(point, mouseSpeed="slow", knotsCount=5)
        else:
            rand_point = table.random_point()
            point: Point = Point(rand_point.x + offset[0], rand_point.y + offset[1])
            self.mouse.move_to(point)
        return True
