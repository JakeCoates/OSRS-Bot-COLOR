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

            if not self.api_m.get_is_inv_full():
                if jug_last:
                    self.jug_loop()
                    self.grape_loop()
                    jug_last = False
                else:
                    self.grape_loop()
                    self.jug_loop()
                    jug_last = True
                if not self.api_m.get_is_inv_full():
                    self.hop_world()
                    time.sleep(2)
            else:
                self.top_stairs_down()
                time.sleep(2)
                self.middle_stairs_action(2)
                time.sleep(2)
                self.fill_jugs_with_water()
                time.sleep(2)
                self.merge_grapes_with_jug()
                time.sleep(2)
                self.bottom_stairs_up()
                time.sleep(2)
                self.middle_stairs_action(1)
                time.sleep(2)

        self.update_progress(1)
        self.__logout("Finished.")
        
    def merge_grapes_with_jug(self):
        start_time = time.time()
        end_time = 7
        while time.time() - start_time < end_time:
            indices_jug = self.api_m.get_inv_item_indices(ids.JUG_OF_WATER)
            indices_grape = self.api_m.get_inv_item_indices(ids.GRAPES)
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
            time.sleep(15)


    def top_stairs_down(self):
        start_time = time.time()
        end_time = 7
        while time.time() - start_time < end_time:

            self.log_msg("Searching for stairs...")
            # If our mouse isn't hovering over a stairs, and we can't find another stairs...
            if not self.mouseover_text(contains="Climb", color=clr.OFF_WHITE) and not self.__move_mouse_to_nearest_marker(clr.CYAN):
                time.sleep(1)
                self.log_msg("failed to find stairs...")
                continue

            # Click if the mouseover text assures us we're clicking a table
            if not self.mouseover_text(contains="Climb", color=clr.OFF_WHITE):
                self.log_msg("failed to find stairs...")
                continue
            self.log_msg("stairs Clicked")
            self.mouse.click()
            time.sleep(2)
            self.update_progress((time.time() - start_time) / end_time)
            break

    def middle_stairs_action(self, action=1):
        # 1 = up
        # 2 = down
        start_time = time.time()
        end_time = 7
        while time.time() - start_time < end_time:

            self.log_msg("Searching for stairs...")
            # If our mouse isn't hovering over a stairs, and we can't find another stairs...
            if not self.mouseover_text(contains="Climb", color=clr.OFF_WHITE) and not self.__move_mouse_to_nearest_marker(clr.BLUE):
                time.sleep(1)
                self.log_msg("failed to find stairs...")
                continue

            # Click if the mouseover text assures us we're clicking a table
            if not self.mouseover_text(contains="Climb", color=clr.OFF_WHITE):
                self.log_msg("failed to find stairs...")
                continue
            self.log_msg("stairs Clicked")
            self.mouse.click()
            time.sleep(2)
            pag.hotkey(f'{action}')
            time.sleep(2)
            self.update_progress((time.time() - start_time) / end_time)
            break

    def bottom_stairs_up(self):
        start_time = time.time()
        end_time = 7
        while time.time() - start_time < end_time:

            self.log_msg("Searching for stairs...")
            # If our mouse isn't hovering over a stairs, and we can't find another stairs...
            if not self.mouseover_text(contains="Climb", color=clr.OFF_WHITE) and not self.__move_mouse_to_nearest_marker(clr.YELLOW):
                time.sleep(1)
                self.log_msg("failed to find stairs...")
                continue

            # Click if the mouseover text assures us we're clicking a table
            if not self.mouseover_text(contains="Climb", color=clr.OFF_WHITE):
                self.log_msg("failed to find stairs...")
                continue
            self.log_msg("stairs Clicked")
            self.mouse.click()
            time.sleep(2)
            self.update_progress((time.time() - start_time) / end_time)
            break

    def hop_world(self):
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
        start_time = time.time()
        end_time = 7
        while time.time() - start_time < end_time:

            self.log_msg("Searching for Jug...")
            # If our mouse isn't hovering over a table, and we can't find another table...
            if not self.mouseover_text(contains="Jug", color=clr.OFF_ORANGE) and not self.__move_mouse_to_nearest_marker(clr.PURPLE, (25, 0)):
                time.sleep(1)
                self.log_msg("failed to find table...")
                continue

            # Click if the mouseover text assures us we're clicking a table
            if not self.mouseover_text(contains="Jug", color=clr.OFF_ORANGE):
                self.log_msg("failed to find Jug...")
                continue
            self.log_msg("Jug Clicked")
            self.mouse.click()
            time.sleep(2)
            self.update_progress((time.time() - start_time) / end_time)
            break

    def grape_loop(self): 
        start_time = time.time()
        end_time = 7
        while time.time() - start_time < end_time:
            
            self.log_msg("Searching for Grapes...")
            # If our mouse isn't hovering over a table, and we can't find another table...
            if not self.mouseover_text(contains="Grapes", color=clr.OFF_ORANGE) and not self.__move_mouse_to_nearest_marker(clr.PINK, (0, -25)):
                time.sleep(1)
                self.log_msg("failed to find table...")
                continue

            # Click if the mouseover text assures us we're clicking a table
            if not self.mouseover_text(contains="Grapes", color=clr.OFF_ORANGE):
                self.log_msg("failed to find Grapes...")
                continue
            self.log_msg("Grapes Clicked")
            self.mouse.click()
            time.sleep(2)
            self.update_progress((time.time() - start_time) / end_time)
            break


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
