import time
from enum import Enum

import pyautogui as pag
from model.osrs.panda.bot_base import PandasBaseBot, WalkTiles
import utilities.api.item_ids as ids
import utilities.color as clr
import utilities.random_util as rd
from model.osrs.osrs_bot import OSRSBot
from model.runelite_bot import BotStatus
from utilities.api.morg_http_client import MorgHTTPSocket
from utilities.api.status_socket import StatusSocket
from utilities.geometry import Point, RuneLiteObject
import utilities.imagesearch as imsearch

class PandaWine(PandasBaseBot):
    def __init__(self):
        bot_title = "Wine"
        description = "This bot power-wines wine"
        super().__init__(bot_title=bot_title, description=description)
        self.running_time = 60
        self.take_breaks = True
        self.afk_train = True
        self.delay_min =0.37
        self.delay_max = .67
        self.wine_count = 100
        # Setup API
        self.api_m = MorgHTTPSocket()
        self.api_s = StatusSocket()

    def create_options(self):
        super().create_options()
        self.options_builder.add_slider_option("wine_count", "How many wines to make?", 1, 5000)

    def save_options(self, options: dict):
        super().save_options(options)
        for option in options:
            if option == "wine_count":
                self.running_time = options[option]
            else:
                self.log_msg(f"Unexpected option: {option}")

        self.log_msg(f"Running time: {self.running_time} minutes.")
        self.log_msg(f"Bot will{'' if self.take_breaks else ' not'} take breaks.")
        self.log_msg(f"Bot will wait between {self.delay_min} and {self.delay_max} seconds between actions.")
        self.log_msg(f"Bot will make {options['wine_count']} wines.")
        self.log_msg("Options set successfully.")
        self.options_set = True

    def main_loop(self):
        # Setup variables
        self.setup()

        while time.time() - self.start_time < self.end_time:

            runtime = int(time.time() - self.start_time)
            minutes_since_last_break = int((time.time() - self.last_break) / 60)
            seconds = int(time.time() - self.last_break) % 60
            percentage = (self.multiplier * .01)  # this is the percentage chance of a break
            deposit_slots = self.api_m.get_inv_item_first_indice(self.deposit_ids)
            self.roll_chance_passed = False

            jugs = self.get_inv_items(ids.JUG_OF_WATER)
            grapes = self.get_inv_items(ids.GRAPES)
            self.log_msg(f'collected {len(jugs)} jugs, collected {len(grapes)} grapes')
            jug_last = False

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

    def setup(self):
        """Sets up loop variables, checks for required items, and checks location.
            This will ideally stop the bot from running if it's not setup correctly.
            * To-do: Add functions to check for required items, bank setup and locaiton.
            Args:
                None
            Returns:
                None"""
        super().setup()
        self.idle_time = 0
        self.deposit_ids = [ids.JUG, ids.JUG_OF_BAD_WINE, ids.JUG_OF_BAD_WINE_1992, ids.JUG_OF_WINE, ids.GRAPES, ids.EMPTY_JUG, ids.JUG_OF_WATER]
        

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

    def bank_walk(self, direction):
        # 1 is towards bank -1 is away from bank
        walking_tiles = [WalkTiles.GUILD, WalkTiles.NEAR_GUILD, WalkTiles.NEAR_BANK, WalkTiles.BANK]
        for tile_color in walking_tiles[::direction]:
            self.attempt_to_walk(f'{tile_color.name}', 'Walk', clr.OFF_WHITE, tile_color.value, 7)
        while not self.api_m.get_is_player_idle():
            self.log_msg("waiting for idle.")
            time.sleep(0.4)


    def guild_door(self):
        self.attempt_to_click('door', 'Open', clr.OFF_WHITE, clr.PURPLE, 7)
        time.sleep(4)

    def bank_use(self):
        self.open_bank()
        time.sleep(1)
        self.deposit_items(self.api_m.get_inv_item_first_indice([ids.JUG_OF_WINE, ids.JUG_OF_BAD_WINE, ids.JUG_OF_BAD_WINE_1992, ids.GRAPES]))
        time.sleep(1)
        pag.hotkey('esc')
        time.sleep(1)
        
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

            self.attempt_to_click('click sink', 'Sink', clr.OFF_CYAN, clr.RED, 7)

            pag.hotkey('space')
            time.sleep(17)


    def top_stairs_down(self):
        while self.api_m.get_player_position()[2] == 2:
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

    def jug_loop(self): 
        if self.api_m.get_is_inv_full():
            return
        self.attempt_to_click('Jug', 'Jug', clr.OFF_ORANGE, clr.PURPLE, 7, (25, 0))

    def grape_loop(self): 
        if self.api_m.get_is_inv_full():
            return
        self.attempt_to_click('Grapes', 'Grapes', clr.OFF_ORANGE, clr.PINK, 7, (0, -25))
