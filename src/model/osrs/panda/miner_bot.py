from pathlib import Path
import time
from enum import Enum

import pyautogui as pag
from model.osrs.panda.bot_base import PandasBaseBot, WalkTiles
import utilities.api.item_ids as ids
import utilities.color as clr
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

class PandaMine(PandasBaseBot):
    def __init__(self):
        bot_title = "Panda Mining"
        description = """Mines at supported locations."""
        super().__init__(bot_title=bot_title, description=description)
        # Set option variables below (initial value is only used during UI-less testing)
        self.running_time = 200
        self.take_breaks = True
        self.afk_train = True
        self.delay_min = 1.37
        self.delay_max = 1.67
        self.ores = ids.ores
        self.power_Mining = False
        self.Mining_tools = ids.pickaxes
        self.bank_direction = "North"
        self.ore_type = OreType.Coal.value
        self.camera_adjusted = False


    def create_options(self):
        """
        Use the OptionsBuilder to define the options for the bot. For each function call below,
        we define the type of option we want to create, its key, a label for the option that the user will
        see, and the possible values the user can select. The key is used in the save_options function to
        unpack the dictionary of options after the user has selected them.
        """
        super().create_options()
        self.options_builder.add_checkbox_option("power_Mining", "Power Mining? Drops everything in inventory.", [" "])
        self.options_builder.add_dropdown_option("bank_direction", "Bank Direction", ["North","East","South","West"])
        self.options_builder.add_dropdown_option("ore_type", "Ore Type", [OreType.Coal.value, OreType.Silver.value, OreType.Iron.value])

    def save_options(self, options: dict):
        """
        For each option in the dictionary, if it is an expected option, save the value as a property of the bot.
        If any unexpected options are found, log a warning. If an option is missing, set the options_set flag to
        False.
        """
        super().save_options(options)
        for option in options:
            if option == "power_Mining":
                self.power_Mining = options[option] != []
            if option == "ore_type":
                self.ore_type = options[option]
            else:
                self.log_msg(f"Unexpected option: {option}")

        self.log_msg(f"Running time: {self.running_time} minutes.")
        self.log_msg(f"Bot will{'' if self.take_breaks else ' not'} take breaks.")
        self.log_msg(f"Bot will{'' if self.afk_train else ' not'} train like you're afk on another tab.")
        self.log_msg(f"Bot will wait between {self.delay_min} and {self.delay_max} seconds between actions.")
        self.log_msg(f"Bot will{'' if self.power_Mining else ' not'} power mine.")
        self.log_msg("Options set successfully.")
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
            deposit_slots = self.api_m.get_first_occurrence(self.deposit_ids)
            self.roll_chance_passed = False

            try:
                while not self.api_m.get_is_inv_full():
                    if self.api_m.get_run_energy() == 10000:
                        self.mouse.move_to(self.win.run_orb.random_point())
                        self.mouse.click()
                        time.sleep(self.random_sleep_length())
                    if Mining_spot := self.get_nearest_tag(clr.PINK):
                        self.go_mining()
                        deposit_slots = self.api_m.get_first_occurrence(self.deposit_ids)
                    else:
                        self.go_to_mine()


                if not self.power_Mining:
                    self.go_to_bank()
                    
                self.bank_or_drop(deposit_slots)
                    

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
        self.logout()
        self.stop()

    def go_to_bank(self):
        if found := self.get_nearest_tag(color=clr.YELLOW):
            return
        world_map_button = imsearch.search_img_in_rect(self.PANDAS_IMAGES.joinpath("world_map.png"), self.win.minimap_area)
        # world_map_button not found means the map is likely already open
        if world_map_button:
            self.mouse.move_to(world_map_button.random_point(), mouseSpeed="medium")
            self.mouse.click()
            time.sleep(self.random_sleep_length(.8, 2.2))

            self.go_to_map_image("varrock_west_bank.png")
    
    def go_to_mine(self):
        world_map_button = imsearch.search_img_in_rect(self.PANDAS_IMAGES.joinpath("world_map.png"), self.win.minimap_area)
        # world_map_button not found means the map is likely already open
        if world_map_button:
            self.mouse.move_to(world_map_button.random_point(), mouseSpeed="medium")
            self.mouse.click()
            time.sleep(self.random_sleep_length(.8, 1.2))

            self.go_to_map_image("varrock_west_mine.png")
            
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
        self.deposit_ids = self.ores
        self.deposit_ids.extend([ids.UNCUT_DIAMOND, ids.UNCUT_DRAGONSTONE, ids.UNCUT_EMERALD, ids.UNCUT_RUBY, ids.UNCUT_SAPPHIRE])
        self.deposit_ids.extend([ids.COINS, ids.COINS_6964, ids.COINS_8890, ids.COINS_995])
        self.deposit_ids.extend([ids.CLUE_GEODE_EASY, ids.CLUE_BOTTLE_BEGINNER, ids.CLUE_BOTTLE_MEDIUM, ids.CLUE_BOTTLE_HARD, ids.CLUE_BOTTLE_ELITE])


        # Setup Checks for pickaxes and tagged objects
        self.check_equipment()

        if not self.power_Mining:
            self.face_north()

        if not self.get_nearest_tag(clr.YELLOW) and not self.get_nearest_tag(clr.PINK) and not self.power_Mining:
            self.log_msg("Did not see a bank(YELLOW) or a Mining spot (PINK) on screen, make sure they are tagged.")
            self.adjust_camera(clr.YELLOW)
            self.camera_adjusted = True
            self.stop()
        
        self.check_bank_settings()


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
        if int(time.time() - time_started) < self.random_sleep_length(.05, .1):
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
                start_trying = time.time()
                while self.check_click_ore(start_trying):
                    if Mining_spot := self.get_nearest_tag(clr.PINK, int(time.time() - start_trying) > 4):
                        self.mouse.move_to(Mining_spot.random_point(), mouseSpeed="fastest")
                self.api_m.wait_til_gained_xp("Mining", timeout=5 * self.ore_difficulty_multiplier())
                self.idle_time = time.time()

            else:
                if int(time.time() - self.idle_time) > 3:
                    self.hop_world()
                if int(time.time() - self.idle_time) > 120:
                    self.adjust_camera(clr.PINK, 1)
                    self.camera_adjusted = True
                if int(time.time() - self.idle_time) > 240:
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
            return 1
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
    