from pathlib import Path
import time
from enum import Enum

import pyautogui as pag
from model.osrs.panda.bot_base import PandasBaseBot, WalkTiles
import utilities.api.item_ids as ids
import utilities.color as clr
import utilities.ocr as ocr
import utilities.random_util as rd
from model.osrs.osrs_bot import OSRSBot
from model.runelite_bot import BotStatus
import utilities.api.animation_ids as animation
from utilities.api.morg_http_client import MorgHTTPSocket
from utilities.api.status_socket import StatusSocket
from utilities.geometry import Point, RuneLiteObject
import utilities.game_launcher as launcher
import utilities.imagesearch as imsearch

class OreType(Enum):
    Coal = "Coal rocks"
    Silver = "Silver rocks"
    Iron = "Iron rocks"

class PandaTravel(PandasBaseBot):
    def __init__(self):
        bot_title = "Panda Travel"
        description = """Mines at supported locations."""
        super().__init__(bot_title=bot_title, description=description)
        self.options_set = True
        # Set option variables below (initial value is only used during UI-less testing)


    def create_options(self):
        """
        Use the OptionsBuilder to define the options for the bot. For each function call below,
        we define the type of option we want to create, its key, a label for the option that the user will
        see, and the possible values the user can select. The key is used in the save_options function to
        unpack the dictionary of options after the user has selected them.
        """
        super().create_options()

    def save_options(self, options: dict):
        """
        For each option in the dictionary, if it is an expected option, save the value as a property of the bot.
        If any unexpected options are found, log a warning. If an option is missing, set the options_set flag to
        False.
        """
        super().save_options(options)

        self.options_set = True


    def launch_game(self):
    
        # If playing RSPS, change `RuneLite` to the name of your game
        if launcher.is_program_running("RuneLite"):
            self.log_msg("RuneLite is already running. Please close it and try again.")
            return
        
        settings = Path(__file__).parent.joinpath("WDMiner.properties")
        launcher.launch_runelite(
            properties_path=settings, 
            game_title=self.game_title, 
            use_profile_manager=True, 
            profile_name="WDMiner", 
            callback=self.log_msg)

    def main_loop(self):
        """
        Main bot loop. We call setup() to set up the bot, then loop until the end time is reached.
        """
        # Setup variables
        self.setup()
        # Main loop
        while time.time() - self.start_time < self.end_time:

            runtime = int(time.time() - self.start_time)
            minutes_since_last_break = int((time.time() - self.last_break) / 60)
            seconds = int(time.time() - self.last_break) % 60
            percentage = (self.multiplier * .01)  # this is the percentage chance of a break

            try:
                # while True:
                # world_map_button = imsearch.search_img_in_rect(self.PANDAS_IMAGES.joinpath("world_map.png"), self.win.minimap_area)
                # # world_map_button not found means the map is likely already open
                # if world_map_button:
                #     self.mouse.move_to(world_map_button.random_point(), mouseSpeed="medium")
                #     self.mouse.click()
                #     time.sleep(self.random_sleep_length(.8, 2.2))

                    try: 
                        furthest_blue = self.search_random_blue_pixel(self.win.minimap)
                        self.mouse.move_to(furthest_blue, mouseSpeed="medium")
                        self.mouse.click()
                        time.sleep(self.random_sleep_length(.1, .2))
                    except:
                        fail_count = fail_count - 1
                        if fail_count <= 0:
                            break

                    # if target is not set
                    # Open map
                    # if inventory full image is bank else mine
                    # find image of above clause
                    # shift right click near enough
                    # set target
                    # exit map
                    
                    # if target is set
                    # use script to run following the target

                    # when close enough to target
                    # shift right click
                    # clear path

            except Exception as e:
                self.log_msg(f"Exception: {e}")
                self.loop_count += 1
                if self.loop_count > 5:
                    self.log_msg("Too many exceptions, stopping.")
                    self.log_msg(f"Last exception: {e}")
                    self.stop()
                continue
     
                
            # -- End bot actions --
            self.loop_count = 0
            if self.take_breaks:
                self.check_break(runtime, percentage, minutes_since_last_break, seconds)
            current_progress = round((time.time() - self.start_time) / self.end_time, 2)
            if current_progress != round(self.last_progress, 2):
                self.update_progress((time.time() - self.start_time) / self.end_time)
                self.last_progress = round(self.progress, 2)

        self.update_progress(1)
        self.log_msg("Finished.")
        # self.logout()
        self.stop()
    
    
    def setup(self):
        """Sets up loop variables, checks for required items, and checks location.
            This will ideally stop the bot from running if it's not setup correctly.
            * To-do: Add functions to check for required items, bank setup and locaiton.
            Args:
                None
            Returns:
                None"""
        super().setup()



    def face_north(self):
        """Faces the player north.
            Args:
                None
            Returns:
                None"""
        self.mouse.move_to(self.win.compass_orb.random_point(), mouseSpeed = "fastest")
        self.mouse.click()


    def check_bank_settings(self):
        """Checks if the bank booth is set to deposit all items.
            Args:
                None
            Returns:
                None"""
        # self.open_bank()
        # self.close_bank()


    def is_Mining(self):
        """
        This will check if the player is currently woodcutting.
        Returns: boolean
        Args: None
        """
        # get the current player animation
        Mining_animation_list = [animation.MINING_ADAMANT_PICKAXE, animation.MINING_BLACK_PICKAXE, animation.MINING_BRONZE_PICKAXE, animation.MINING_DRAGON_PICKAXE, animation.MINING_IRON_PICKAXE, animation.MINING_MITHRIL_PICKAXE, animation.MINING_RUNE_PICKAXE, animation.MINING_STEEL_PICKAXE]
        current_animation = self.api_m.get_animation_id()

        # check if the current animation is woodcutting
        return current_animation in Mining_animation_list

    def check_click_ore(self, time_started):
        if int(time.time() - time_started) < 2:
            return not self.mouseover_text(contains=self.ore_type, color=clr.OFF_CYAN) or not self.mouse.click(check_red_click=True)
        else:
            return self.mouseover_text(contains="Attack", color=clr.OFF_WHITE) or  self.mouseover_text(contains="Talk", color=clr.OFF_WHITE) or not self.mouse.click(check_red_click=True)

    def go_mining(self):
        """
        This will go Mining.
        Returns: void
        Args: None
        """
        self.breaks_skipped = 0
        afk_time = 0
        afk__start_time = time.time()

        self.is_runelite_focused()   # check if runelite is focused
        if not self.is_focused:
            self.log_msg("Runelite is not focused...")
        while not self.api_m.get_is_inv_full(): 
            afk_time = int(time.time() - afk__start_time)
            if Mining_spot := self.get_nearest_tag(clr.PINK):
                self.mouse.move_to(Mining_spot.random_point())
                start_trying = time.time()
                while self.check_click_ore(start_trying):
                    if Mining_spot := self.get_nearest_tag(clr.PINK, int(time.time() - start_trying) > 4):
                        self.mouse.move_to(Mining_spot.random_point())
                self.api_m.wait_til_gained_xp("Mining", timeout=20 * self.ore_difficulty_multiplier())
                self.idle_time = time.time()

            else:
                if int(time.time() - self.idle_time) > 2:
                    self.hop_world()
                if int(time.time() - self.idle_time) > 32:
                    if self.get_nearest_tag(clr.CYAN):
                        self.mouse.move_to(self.get_nearest_tag(clr.CYAN).random_point())
                        self.mouse.click()
                    time.sleep(self.random_sleep_length())
                if int(time.time() - self.idle_time) > 60:
                    self.adjust_camera(clr.PINK, 1)
                    self.camera_adjusted = True
                if int(time.time() - self.idle_time) > 120:
                    self.log_msg("No Mining spot found in 60 seconds, quitting bot.")
                    self.stop()
            self.breaks_skipped = afk_time // 15

        if self.breaks_skipped > 0:
            self.roll_chance_passed = True
            self.multiplier += self.breaks_skipped * .25
            self.log_msg(f"Skipped {self.breaks_skipped} break rolls while mining.")
        return


    def bank_or_drop(self, deposit_slots):
        """
        This will either bank or drop items depending on the power_Mining setting.
        Returns: void
        Args: None"""
        if not self.power_Mining:
            self.open_bank()
            time.sleep(self.random_sleep_length())
            self.check_deposit_all()
            self.deposit_items(deposit_slots, self.deposit_ids)
            time.sleep(self.random_sleep_length())
            self.close_bank()
            time.sleep(self.random_sleep_length())
        else:
            self.drop_all(skip_slots=self.api_m.get_inv_slots_with_items(self.Mining_tools))

    def check_equipment(self):
        """
        Stops script if no axe is equipped.
        Returns: none
        Args: None
        """
        if not self.api_m.get_if_item_in_inv(self.Mining_tools) and not self.api_m.get_is_item_equipped(self.Mining_tools):
            self.log_msg("No Mining tool or in inventory, please fix that...")
            self.stop()

    def walk_to_color(self, color: clr, direction: int):
        """
        Walks to the bank.
        Returns: void
        Args: None"""
        # find and click furthest CYAN tile till "color" tile is found
        switch_direction = False
        time_start = time.time()
        while True:
            if self.camera_adjusted:
                self.face_north()
                self.camera_adjusted = False
            # When walking to bank lets check if we need to switch directions so it's a smoother walk by checking the minimap
            if color == clr.YELLOW:
                if change_direction_img := imsearch.search_img_in_rect(self.PANDAS_IMAGES.joinpath("varrock_east_minimap.png"), self.win.minimap):
                    switch_direction = True
            if time.time() - time_start > 240:
                self.log_msg("We've been walking for 4 minutes, something is wrong...stopping.")
                self.stop()
            if found := self.get_nearest_tag(color):
                break
            shapes = self.get_all_tagged_in_rect(self.win.game_view, clr.CYAN)
            if shapes is []:
                self.log_msg("No cyan tiles found, stopping.")
                return
            if len(shapes) > 1:
                shapes_sorted = (
                    sorted(shapes, key=get_direction_point(self.bank_direction))
                )
                self.mouse.move_to(shapes_sorted[0 if direction == 1 else -1].random_point(), mouseSpeed = "fastest")                    
            else:
                self.mouse.move_to(shapes[0].random_point(), mouseSpeed = "fastest")
            self.mouse.click()
            time.sleep(self.random_sleep_length(.35, .67))
        return
    
    def ore_difficulty_multiplier(self):
        if(OreType(self.ore_type) == OreType.Iron):
            return 1.5
        if(OreType(self.ore_type) == OreType.Silver):
            return 2
        if(OreType(self.ore_type) == OreType.Coal):
            return 4
        
def get_direction_point(bank_direction):
    if(bank_direction == "North"):
        return RuneLiteObject.distance_from_top_center
    if(bank_direction == "East"):
        return RuneLiteObject.distance_from_rect_right
    if(bank_direction == "South"):
        return RuneLiteObject.distance_from_bottom_center
    if(bank_direction == "West"):
        return RuneLiteObject.distance_from_rect_left
    