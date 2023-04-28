from abc import ABCMeta
from typing import Tuple, Union, List
from pathlib import Path
import random
import threading
import time
from enum import Enum

import pyautogui as pag
import utilities.api.item_ids as ids
import utilities.color as clr
import utilities.game_launcher as launcher
import utilities.random_util as rd
from model.osrs.osrs_bot import OSRSBot
from model.runelite_bot import BotStatus
from utilities.api.morg_http_client import MorgHTTPSocket
from utilities.api.status_socket import StatusSocket
from utilities.geometry import Point, RuneLiteObject
import utilities.imagesearch as imsearch

class TileDetails():
    def __init__(self, color, world_pos):
        self.Color: clr.Color = color
        self.WorldPos: Tuple[int, int, int] = world_pos

class WalkTiles(Enum):
    BANK = TileDetails(clr.PINK, [3183, 3448, 0])
    NEAR_BANK = TileDetails(clr.GREEN, [3170, 3452, 0])
    NEAR_GUILD = TileDetails(clr.BLUE, [3156, 3449, 0])
    GUILD = TileDetails(clr.CYAN, [3145, 3442, 0])


class PandasBaseBot(OSRSBot, launcher.Launchable, metaclass=ABCMeta):
    
    # Update the BOT_IMAGES path
    PANDAS_IMAGES = Path(__file__).parent.joinpath("images")

    def __init__(self, bot_title, description):
        super().__init__(bot_title, description)
        self.running_time = 1
        self.take_breaks = False

    def create_options(self):
        self.options_builder.add_slider_option("running_time", "How long to run (minutes)?", 1, 500)
        self.options_builder.add_checkbox_option("take_breaks", "Take breaks?", [" "])
        self.options_builder.add_slider_option("delay_min", "How long to take between actions (min) (MiliSeconds)?", 300,1200)
        self.options_builder.add_slider_option("delay_max", "How long to take between actions (max) (MiliSeconds)?", 350,1200)

    def save_options(self, options: dict):
        for option in options:
            if option == "running_time":
                self.running_time = options[option]
            elif option == "take_breaks":
                self.take_breaks = options[option] != []
            elif option == "delay_min":
                self.delay_min = options[option]/1000
            elif option == "delay_max":
                self.delay_max = options[option]/1000

    def launch_game(self):
    
        # If playing RSPS, change `RuneLite` to the name of your game
        if launcher.is_program_running("RuneLite"):
            self.log_msg("RuneLite is already running. Please close it and try again.")
            return
        
        settings = Path(__file__).parent.joinpath("panda.properties")
        launcher.launch_runelite(
            properties_path=settings, 
            game_title=self.game_title, 
            use_profile_manager=True, 
            profile_name="Panda", 
            callback=self.log_msg)

    def setup(self):
        """Sets up loop variables, checks for required items, and checks location.
        This will ideally stop the bot from running if it's not setup correctly.
        * To-do: Add functions to check for required items, bank setup and locaiton.
        Args:
            None
        Returns:
            None"""
        self.start_time = time.time()
        self.end_time = self.running_time * 60
        self.is_focused = self.is_runelite_focused()
        self.roll_chance_passed = False
        self.last_progress = 0
        self.breaks_skipped = 0
        self.last_break = time.time()
        self.multiplier = 1
        self.loop_count = 0
        self.api_m = MorgHTTPSocket()
        self.api_s = StatusSocket()
        self.spec_energy = self.get_special_energy()
        self.last_runtime = 0
        self.safety_squares = self.get_all_tagged_in_rect(self.win.game_view ,clr.CYAN)
        
    def is_runelite_focused(self):
        """
        This will check if the runelite window is focused.
        Returns: boolean
        Args: None
        """
        # Get the currently focused window
        current_window = pag.getActiveWindow()

        # Check if the window title contains a certain keyword (e.g. "Google Chrome")
        if current_window is None:
            return False
        if "runelite" in current_window.title.lower():
            self.is_focused = True
            return True
        else:
            self.is_focused = False
            return False


    def activate_special(self):
        """Activates the special attack of the equipped weapon.
            Args:
                None
            Returns:
                None"""
        self.mouse.move_to(self.win.spec_orb.random_point())
        time.sleep(self.random_sleep_length(.8, 1.2))
        self.mouse.click()
        time.sleep(self.random_sleep_length())

    def sleep(self, percentage):
        """Sleeps for a random amount of time between the min and max delay. While player is doing an action.
            Args:
                None
            Returns:
                None"""
        self.breaks_skipped = 0
        afk_time = 0
        afk__start_time = time.time() 

        while not self.api_m.get_is_player_idle():
            time.sleep(self.random_sleep_length(.65, 2.2))
            afk_time = int(time.time() - afk__start_time)
            self.is_runelite_focused()
            self.breaks_skipped = afk_time // 15

        if self.breaks_skipped > 0:
            self.roll_chance_passed = True
            self.multiplier += self.breaks_skipped * .25
            self.log_msg(f"Skipped {self.breaks_skipped} break rolls while afk, percentage chance is now {round((self.multiplier * .01) * 100)}%")

    def random_sleep_length(self, delay_min=0, delay_max=0):
        """Returns a random float between min and max"""
        if delay_min == 0:
            delay_min = self.delay_min
        if delay_max == 0:
            delay_max = self.delay_max
        return rd.fancy_normal_sample(delay_min, delay_max)
    
    def switch_window(self):
        """
        This will switch the window to runelite.
        Returns: void
        Args: None
        """
        # Get the currently focused window
        old_window = pag.getActiveWindow()

        pag.hotkey("alt", "tab")
        new_window = pag.getActiveWindow()

        self.log_msg(f"Switched to window: {new_window.title}.")

        self.is_focused = "RuneLite" in new_window.title
        if old_window.title == new_window.title:
            self.log_msg("Window not switched, something is wrong, quitting bot.")
            self.stop()

        time.sleep(self.random_sleep_length())

    def check_break(self, runtime, percentage, minutes_since_last_break, seconds):
        """
        This will roll the chance of a break.
        Returns: void
        Args:
            runtime: int
            percentage: float
            minutes_since_last_break: int
            seconds: int
            deposit_slots: list
            self.roll_chance_passed: boolean"""
        if runtime % 15 == 0 and runtime != self.last_runtime:
            if runtime % 60 == 0:   # every minute log the chance of a break
                self.log_msg(f"Chance of random break is {round(percentage * 100)}%")

            self.roll_break(
                percentage, minutes_since_last_break, seconds
            )

        elif self.roll_chance_passed:
            self.log_msg(f"Chance of random break is {round(percentage * 100)}%")

            self.roll_break(
                percentage, minutes_since_last_break, seconds
            )
        self.last_runtime = runtime

    def roll_break(self, percentage, minutes_since_last_break, seconds):
        if (
            rd.random_chance(probability=percentage / (1 if self.afk_train else 4))   # when afk theres weird timing issues so we divide by 4 if not afk
            and self.take_breaks
        ):
            self.reset_timer(
                minutes_since_last_break, seconds, percentage
            )
        self.multiplier += .25  # increase multiplier for chance of random break, we want + 1% every minute 
        self.roll_chance_passed = False

    def reset_timer(self, minutes_since_last_break, seconds, percentage):
        self.log_msg(f"Break time, last break was {minutes_since_last_break} minutes and {seconds} seconds ago. \n Chance of random break was {round(percentage * 100)}%")

        self.last_break = time.time()   # reset last break time
        self.multiplier = 1    # reset multiplier

        self.take_random_break(minutes_since_last_break)

    def take_menu_break(self):
        """
        This will take a random menu break [Skills, Combat].]
        Returns: void
        Args: None
        """
        # random amount of seconds to teak a break
        break_time = random.uniform(1, 15)

        if rd.random_chance(.7):
            self.log_msg("Taking a Sklls Tab break...")
            self.mouse.move_to(self.win.cp_tabs[1].random_point())
            time.sleep(self.random_sleep_length())
            if self.mouseover_text(contains="Skills", color=clr.OFF_WHITE):
                self.mouse.click()
                self.mouse.move_to(self.win.control_panel.random_point())
                time.sleep(break_time)

                # go back to inventory
                self.mouse.move_to(self.win.cp_tabs[3].random_point())
                time.sleep(self.random_sleep_length())
                if self.mouseover_text(contains="Inventory", color=clr.OFF_WHITE):
                    self.mouse.click()
            else:
                self.log_msg("Skills tab not found, break function didn't work...")
                self.stop()
        else:
            self.log_msg("Taking an Equipment menu break...")
            self.mouse.move_to(self.win.cp_tabs[4].random_point())
            time.sleep(self.random_sleep_length())
            if self.mouseover_text(contains="Worn", color=clr.OFF_WHITE):
                self.mouse.click()

                self.mouse.move_to(self.win.control_panel.random_point())
                time.sleep(break_time)

                # go back to inventory
                self.mouse.move_to(self.win.cp_tabs[3].random_point())
                if self.mouseover_text(contains="Inventory", color=clr.OFF_WHITE):
                    self.mouse.click()

            else:
                self.log_msg("Combat tab not found, break function didn't work...")
                self.stop()
        return

    def take_random_break(self, minutes_since_last_break):
        """This will randomly choose a break type and take it. The shorter time since last break, the more likely it is to be a menu break.
        Returns: void
        Args: minutes_since_last_break (int) - the number of minutes passed since the last break."""
        # break type is a random choice from list
        break_type = random.choice(["menu", "break"])

        if break_type == "menu":
            self.take_menu_break()

        if break_type == "break":
            self.log_msg("Taking a break...")

            # check if player is idle
            while not self.api_m.get_is_player_idle():
                self.log_msg("Player is not idle, waiting for player to be idle before taking break...")
                time.sleep(self.random_sleep_length(3,8))

            if minutes_since_last_break > 15:
                self.take_break(15, 120)
            else:
                self.take_break()

    def attempt_to_click(self, text, contains_word, contains_color, marker_color, end_time=7, offset=(0,0)) -> bool:
        start_time = time.time()
        result = False
        while time.time() - start_time < end_time:
            self.log_msg(f'Searching for {text}...')
            # If our mouse isn't hovering over the object, and we can't find another object...
            if not self.mouseover_text(contains=contains_word, color=contains_color) and not self.__move_mouse_to_nearest_marker(marker_color, offset):
                time.sleep(self.random_sleep_length(1,2))
                self.log_msg(f'failed to find {contains_word}...')
                continue

            time.sleep(self.random_sleep_length(0.05,0.1))
            # Click if the mouseover text assures us we're clicking the object
            if not self.mouseover_text(contains=contains_word, color=contains_color):
                self.log_msg(f'failed to find {contains_word}...')
                continue
            self.log_msg(f'{text} Clicked')
            self.mouse.click()
            time.sleep(self.random_sleep_length(1,2))
            # return true as it managed to click
            result = True
            break
        return result

    def attempt_to_walk(self, text, contains_word, contains_color, tile: TileDetails, end_time=7, offset=(0,0)):
        start_time = time.time()
        result = False
        while time.time() - start_time < end_time:

            self.log_msg(f'Searching for {text}...')
            # If our mouse isn't hovering over the object, and we can't find another object...
            if not self.__move_mouse_to_nearest_marker(tile.Color, offset):
                time.sleep(self.random_sleep_length(1,2))
                self.log_msg(f'failed to find {text}...')
                continue

            time.sleep(self.random_sleep_length(0.05, 0.15))
            # Click if the mouseover text assures us we're clicking the object
            if not self.mouseover_text(contains=contains_word, color=contains_color):
                self.log_msg(f'failed to find {text}...')
                continue
            self.log_msg(f'{text} Clicked')
            self.mouse.click()
            time.sleep(self.random_sleep_length(1,2))
            player_pos = self.api_m.get_player_position()
            if player_pos[0] - tile.WorldPos[0] < 3 and player_pos[0] - tile.WorldPos[0] > -3:
            # Within +-3 of x
                if player_pos[1] - tile.WorldPos[1] < 3 and player_pos[1] - tile.WorldPos[1] > -3:
                # Within +-3 of y
                    result = True
                    break
        return result

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

        attempts = 0
        wait_time = time.time()
        while not self.is_bank_open():

            if attempts > 5:
                # if we waited for 10 seconds, break out of loop
                if time.time() - wait_time > 40:
                    self.log_msg("We clicked on the bank but player is not idle after 40 seconds, something is wrong, quitting bot.")
                    self.stop()
            else:
                bank = self.choose_bank()

                # move mouse to bank and click
                self.mouse.move_to(bank.random_point())
                while not self.mouseover_text(contains="Bank booth", color=clr.OFF_CYAN) or not self.mouse.click(check_red_click=True):
                    if Mining_spot := self.get_nearest_tag(clr.YELLOW):
                        self.mouse.move_to(Mining_spot.random_point())

                time.sleep(self.random_sleep_length(1.8, 3.3))
                attempts += 1
        return

    def check_text(self, object: RuneLiteObject, text):
        """
        calls mouseover text in a loop
        Returns: void
        Args: None
        """
        if not isinstance(text, list):
            text = [text]

        time_searching = time.time()
        search_tries = 1

        while all(txt not in self.mouseover_text() for txt in text):
            time.sleep(self.random_sleep_length(.1, .2))

            if time.time() - time_searching > 2:
                self.mouse.move_to(object.random_point())

            if time.time() - time_searching > 4:
                msg = f"Did not see any of {text} in mouseover text after {search_tries} searches, quitting bot so you can fix it..."
                self.log_msg(msg)
                self.stop()

            search_tries += 1

    def check_deposit_all(self):
        """
        This will check if deposit all png is found, and select all if not.
        """
        # get the path of deposit_all_grey.png and red
        deposit_all_grey = self.PANDAS_IMAGES.joinpath("deposit_all_grey.png")
        deposit_all_red = self.PANDAS_IMAGES.joinpath("deposit_all_red.png")

        # if we find deposit all red in game view, return, else, find grey and click
        time_searching = time.time()
        while True:
            if deposit_all_red_button := imsearch.search_img_in_rect(
                deposit_all_red, self.win.game_view
            ):
                return   # We found deposit all is already selected, return.
            # We now check several times within 1 second for deposit all grey, if we find it, click it and return.
            elif deposit_all_grey_button := imsearch.search_img_in_rect(
                deposit_all_grey, self.win.game_view
            ):
                self.mouse.move_to(deposit_all_grey_button.random_point())
                self.mouse.click()
                return
            if time.time() - time_searching > 1:
                self.log_msg("Could not verifty deposit all settings, double check those.")
                return
            time.sleep(.2)

    class StoppableThread(threading.Thread):
        """Thread class with a stop() method. The thread itself has to check.
            Useful for looking for a tag while main thread is doing something else."""
        def __init__(self, target=None, args=()):
            super().__init__(target=target, args=args)
            self._stop_event = threading.Event()

        def stop(self):
            self._stop_event.set()

        def stopped(self):
            return self._stop_event.is_set()


    def click_in_bank(self, item, amount=1):
        """
        Clicks on an item in the bank x times.
        Args:
            item (RuneLiteObject) - Item to click on
            amount (int) - Number of times to click on item
        Returns:
            void"""
        
        for _ in range(amount):
            self.mouse.move_to(item.random_point())
            self.mouse.click()
            time.sleep(self.random_sleep_length())


    def withdraw_items(self, items: Union[Path, List[Path]], count=1) -> bool:
        """
        Withdraws the correct amount of ingredients from the bank.
        Returns True if all items are found and clicked, False otherwise.
        """

        def find_and_click(item_img: Path) -> bool:
            item_found = None
            time_looking_for_item = time.time() + 5
            while time.time() < time_looking_for_item and not item_found:
                # try several times to find it
                item_found = imsearch.search_img_in_rect(item_img, self.win.game_view)
                if item_found:
                    break
            if not item_found:
                self.log_msg(f"Could not find {item_img.stem} in bank, out of supplies...")
                return False
            else:
                self.click_in_bank(item_found, count)
                return True

        # Convert the input to a list if it's a single Path object
        if isinstance(items, Path):
            items = [items]

        all_items_found = True
        for item_path in items:
            item_found = find_and_click(item_path)
            if not item_found:
                all_items_found = False

        return all_items_found


    def deposit_items(self, slot_list, deposit_ids):
        """
        Clicks once on each unique item to deposit all matching items in the inventory to the bank.
        Bank must be open already.
        Deposit "All" must be selected.
        Args:
            slot_list: list of inventory slots to deposit items from
        Returns:
            None/Void
        """
        if slot_list == -1:
            # If there are no items to deposit, log a message and return early
            self.log_msg("No items to deposit, continuing...")
            return
        if slot_list == 0:
            # If there's only one item, it is the first slot
            slot_list = [0]
        # Loop until there are no more items in the inventory that match the deposit_ids
        while self.api_m.get_inv_item_first_indice(deposit_ids) != -1:
            # Move the mouse to each slot in the inventory and click to deposit all matching items
            for slot in slot_list:
                self.mouse.move_to(self.win.inventory_slots[slot].random_point(), mouseSpeed = "fast")
                self.mouse.click()
                time.sleep(self.random_sleep_length())

        self.log_msg("Finished depositing items")
        return


    def face_north(self):
        """Faces the player north.
            Args:
                None
            Returns:
                None"""
        # Move the mouse to the compass orb and click it to face north
        self.mouse.move_to(self.win.compass_orb.random_point(), mouseSpeed = "fastest")
        self.mouse.click()
    
    def is_hopping_worlds(self):
        """Makes sure we're currently hopping worlds
        Returns:
            True if hopping worlds, False if not
        Args:
            None"""
        please_wait_img = self.PANDAS_IMAGES.joinpath("please_wait.png")
        end_time = time.time() + 3

        while (time.time() < end_time):
            if please_wait := imsearch.search_img_in_rect(please_wait_img, self.win.mouseover):
                return True
            time.sleep(.1)
        return False   

    def close_bank(self):
        """Exits bank by sending escape key"""
        pag.press("esc")
        return

    def is_bank_open(self):
        """Makes sure bank is open, if not, opens it
        Returns:
            True if bank is open, False if not
        Args:
            None"""
        Desposit_all_img = self.PANDAS_IMAGES.joinpath("bank_all.png")
        end_time = time.time() + 3

        while (time.time() < end_time):
            if deposit_btn := imsearch.search_img_in_rect(Desposit_all_img, self.win.game_view):
                return True
            time.sleep(.1)
        return False   
    
    def choose_safety_square(self):
        """
        Choose one of the safe squares to click
        Returns: Rect object
        Args: None
        """
        if self.safety_squares:
            return random.choice(self.safety_squares)
        
        self.log_msg("No Cyan safety squares found, trying to adjust camera...")
        return

    def go_to_safety_square(self):
        """
        Go to a safety square to search for next object to click
        Returns: void
        Args: None
        """
        if safety_square := self.choose_safety_square():
            self.mouse.move_to(safety_square.random_point())
            self.mouse.click()
            # wait till idle
            while not self.api_m.get_is_player_idle():
                time.sleep(self.random_sleep_length(.2, .4))
                return
        return


    def adjust_camera(self, color, timeout=4):
        """
        Adjusts the camera to look for a specific color. Times out after searching 4 seconds
        Args:
            color: color to look for
        Returns:
            None/Void"""
        random_x = random.randint(90, 180) 
        start_time = time.time() # lets make sure we don't wait too long

        # chance for x to be negative
        if random.randint(0, 1) == 1:
            random_x *= -1
        random_xy = (random_x, 0)  # tuple of random x and y

        # call the camera function on a new thread
        camera_thread = self.StoppableThread(target=self.move_camera, args=(random_xy))
        camera_thread.start()   

        while not self.get_nearest_tag(color):
            time_searching = time.time() - start_time

            if time_searching > timeout:
                self.log_msg(f"Could not find highlighted color in {timeout} seconds...")
                camera_thread.stop()    
                return False
            time.sleep(self.random_sleep_length(.1, .2))
        camera_thread.stop()
        time.sleep(self.random_sleep_length())
        return True

    def get_inv_items(self, item):
        return self.api_m.get_inv_item_indices(item)
        

    def hop_world(self):
        if not self.api_m.get_is_inv_full():
            pag.hotkey('ctrl', 'shift', 'right')
            time.sleep(self.random_sleep_length(1.5,3))
            
            pag.hotkey('space')
            time.sleep(self.random_sleep_length(1.5,3))
            pag.hotkey('2')

            wait_time = time.time()
            while self.is_hopping_worlds():
                # if we waited for 10 seconds, break out of loop
                if time.time() - wait_time > 20:
                    break
                time.sleep(self.random_sleep_length(.8, 1.3))

            self.log_msg("Selecting inventory...")
            self.mouse.move_to(self.win.cp_tabs[3].random_point())
            self.mouse.click()


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
            self.mouse.move_to(point, mouseSpeed="fastest", knotsCount=5)
        else:
            rand_point = table.random_point()
            point: Point = Point(rand_point.x + offset[0], rand_point.y + offset[1])
            self.mouse.move_to(point)
        return True
