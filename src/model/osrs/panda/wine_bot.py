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
        self.wine_made = 0
        self.bad_wine_made = 0
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
    
    def inventory_announce(self):
        GRAPES = len(self.api_m.get_inv_item_indices(ids.GRAPES))
        EMPTY_JUGS = len(self.api_m.get_inv_item_indices(ids.EMPTY_JUG))
        JUG = len(self.api_m.get_inv_item_indices(ids.JUG))
        JUG_OF_WATER = len(self.api_m.get_inv_item_indices(ids.JUG_OF_WATER))
        JUG_OF_WINE = len(self.api_m.get_inv_item_indices(ids.JUG_OF_WINE))
        JUG_OF_BAD_WINE = len(self.api_m.get_inv_item_indices(ids.JUG_OF_BAD_WINE))
        JUG_OF_BAD_WINE_1992 = len(self.api_m.get_inv_item_indices(ids.JUG_OF_BAD_WINE_1992))
        self.log_msg(
            f'Currently we have: \n'
            f'{GRAPES} Grapes \n'
            f'{EMPTY_JUGS} Empty Jugs \n'
            f'{JUG} Jugs \n'
            f'{JUG_OF_WATER} Jugs of water \n'
            f'{JUG_OF_WINE} Jugs of wine \n'
            f'{JUG_OF_BAD_WINE} Jugs of Bad win \n'
            f'{JUG_OF_BAD_WINE_1992} Jugs of Bad win 1992?? \n'
        )
    
    def wine_update(self):
        self.wine_made += len(self.api_m.get_inv_item_indices(ids.JUG_OF_WINE))
        self.bad_wine_made += len(self.api_m.get_inv_item_indices(ids.JUG_OF_BAD_WINE))
        self.bad_wine_made += len(self.api_m.get_inv_item_indices(ids.JUG_OF_BAD_WINE_1992))
        self.log_msg(
            f'Wine totals: \n'
            f'{self.wine_made} Good Wine! \n'
            f'{self.bad_wine_made} Bad Wine! \n'
        )

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

            jugs = self.get_inv_items(ids.JUG)
            grapes = self.get_inv_items(ids.GRAPES)
            self.log_msg(f'collected {len(jugs)} jugs, collected {len(grapes)} grapes, created {self.wine_made} wine') 

            # -- run all actions for the bots --

            if not self.api_m.get_is_inv_full() and self.count_made_wine() == 0:
                self.jug_action()
            elif self.count_wine_material_pairs() > 0:
                self.make_wine_action()
            else:
                self.get_to_bank_and_back()

            # -- End bot actions --
            if self.take_breaks:
                self.check_break(runtime, percentage, minutes_since_last_break, seconds)
            current_progress = round((time.time() - self.start_time) / self.end_time, 2)
            if current_progress != round(self.last_progress, 2):
                self.update_progress((time.time() - self.start_time) / self.end_time)
                self.last_progress = round(self.progress, 2)

            progress = self.wine_made / self.wine_count
            self.update_progress(progress)
            if progress > 1:
                break

        self.__logout("Finished.")
    
    def jug_action(self):
        if self.jug_last:
            self.jug_loop()
            self.grape_loop()
            self.jug_last = False
        else:
            self.grape_loop()
            self.jug_loop()
            self.jug_last = True
        self.inventory_announce()
        self.hop_world()

    def make_wine_action(self):
        self.inventory_announce()
        if not self.api_m.get_player_position()[2] == 0: 
            self.get_downstairs()
        if self.count_wine_materials() > 0:
            self.make_wine()

    def get_to_bank_and_back(self):
        self.guild_door()
        self.bank_walk(1)
        self.inventory_announce()
        self.wine_update()
        self.bank_use()
        self.bank_walk(-1)
        self.guild_door()
        self.get_upstairs()

    def count_made_wine(self):
        return len(self.api_m.get_inv_item_indices([ids.JUG_OF_WINE, ids.JUG_OF_BAD_WINE, ids.JUG_OF_BAD_WINE_1992]))
    
    def count_wine_materials(self):
        return len(self.api_m.get_inv_item_indices([ids.GRAPES, ids.JUG_OF_WATER]))
    
    def count_wine_material_pairs(self):
        return min(len(self.api_m.get_inv_item_indices([ids.JUG_OF_WATER])), len(self.api_m.get_inv_item_indices([ids.GRAPES])))

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
        self.jug_last = False
        

    def get_downstairs(self):
        self.top_stairs_down()
        time.sleep(self.random_sleep_length(1.5, 3))
        self.middle_stairs_action(2)
        time.sleep(self.random_sleep_length(1.5, 3))
    
    def get_upstairs(self):
        self.bottom_stairs_up()
        time.sleep(self.random_sleep_length(1.5, 3))
        self.middle_stairs_action(1)
        time.sleep(self.random_sleep_length(1.5, 3))

    def make_wine(self):
        if len(self.api_m.get_inv_item_indices([ids.JUG])) > 0:
            self.fill_jugs_with_water()
            time.sleep(self.random_sleep_length(1.5, 3))
        
        if len(self.api_m.get_inv_item_indices([ids.JUG_OF_WATER])) > 0 and len(self.api_m.get_inv_item_indices([ids.GRAPES])):
            self.merge_grapes_with_jug()
            time.sleep(self.random_sleep_length(1.5, 3))

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
        time.sleep(self.random_sleep_length(4, 6))

    def bank_use(self):
        self.open_bank()
        time.sleep(self.random_sleep_length(1,2.5))
        self.deposit_items(self.api_m.get_inv_item_first_indice([ids.JUG_OF_WINE, ids.JUG_OF_BAD_WINE, ids.JUG_OF_BAD_WINE_1992, ids.GRAPES]))
        time.sleep(self.random_sleep_length(1,2.5))
        pag.hotkey('esc')
        time.sleep(self.random_sleep_length(1,2.5))
        
    def merge_grapes_with_jug(self):
        wait_to_finish = True
        indices_jug = self.get_inv_items(ids.JUG_OF_WATER)
        indices_grape = self.get_inv_items(ids.GRAPES)

        self.mouse.move_to(self.win.inventory_slots[indices_jug[0]].random_point())
        self.mouse.click()
        time.sleep(self.random_sleep_length(0,1))
        self.mouse.move_to(self.win.inventory_slots[indices_grape[0]].random_point())
        self.mouse.click()
        time.sleep(self.random_sleep_length(1,3))
        pag.hotkey('space')
        
        max_seconds_to_wait = 0
        while wait_to_finish and not len(self.api_m.get_inv_item_indices(ids.JUG_OF_WATER)) == 0:
            max_seconds_to_wait += 1
            time.sleep(self.random_sleep_length(1,2.5))
            if max_seconds_to_wait > 30:
                break

        
    def fill_jugs_with_water(self):
        attempts = 0
        wait_to_finish = False
        while not len(self.api_m.get_inv_item_indices(ids.JUG)) == 0:
            attempts += 1

            indices_jug = self.api_m.get_inv_item_indices(ids.JUG)
            self.mouse.move_to(self.win.inventory_slots[indices_jug[0]].random_point())
            self.mouse.click()
            time.sleep(self.random_sleep_length(1.5, 3))

            if self.attempt_to_click('click sink', 'Sink', clr.OFF_CYAN, clr.RED, 7):
                pag.hotkey('space')
                wait_to_finish = True
                break
            if attempts >= 5:
                break
        
        max_seconds_to_wait = 0
        while wait_to_finish and not len(self.api_m.get_inv_item_indices(ids.JUG)) == 0:
            max_seconds_to_wait += 1
            time.sleep(self.random_sleep_length(1,2.5))
            if max_seconds_to_wait > 30:
                break



    def top_stairs_down(self):
        attempts = 0
        while self.api_m.get_player_position()[2] == 2:
            attempts += 1
            self.log_msg(f'player is at position {self.api_m.get_player_position()[2]} attempting to go downstairs')
            attempted_to_click = self.attempt_to_click('top stairs', 'Climb', clr.OFF_WHITE, clr.CYAN, 7)
            if attempted_to_click:
                time.sleep(self.random_sleep_length(1,3))
            if attempts >= 5:
                break


    def middle_stairs_action(self, action=1):
        # 1 = up
        # 2 = down
        attempts = 0
        while self.api_m.get_player_position()[2] == 1:
            attempts += 1
            self.log_msg(f'player is at position {self.api_m.get_player_position()[2]} attempting to go {"Upstairs" if action == 1 else "Downstairs"}')
            attempted_to_click = self.attempt_to_click('middle stairs', 'Climb', clr.OFF_WHITE, clr.BLUE, 7)
            if attempted_to_click:
                time.sleep(self.random_sleep_length(1,3))
            time.sleep(self.random_sleep_length(1.5, 3))
            pag.hotkey(f'{action}')
            time.sleep(self.random_sleep_length(1.5, 3))
            if attempts >= 5:
                break

    def bottom_stairs_up(self):
        attempts = 0
        while self.api_m.get_player_position()[2] == 0:
            attempts += 1
            attempted_to_click = self.attempt_to_click('bottom stairs', 'Climb', clr.OFF_WHITE, clr.YELLOW, 7)
            if attempted_to_click:
                time.sleep(self.random_sleep_length(1,3))
            if attempts >= 5:
                break

    def jug_loop(self): 
        if self.api_m.get_is_inv_full():
            return
        item_start_count = len(self.api_m.get_inv_item_indices(ids.JUG))
        attempts = 0
        
        while len(self.api_m.get_inv_item_indices(ids.JUG)) == item_start_count:
            attempts += 1
            self.log_msg(f'jug attempt {attempts}')
            attempted_to_click = self.attempt_to_click('Jug', 'Jug', clr.OFF_ORANGE, clr.PURPLE, 7, (25, 0))
            if attempted_to_click:
                time.sleep(self.random_sleep_length(1,3))
                self.log_msg(f'initial jugs {item_start_count} new jug count {len(self.api_m.get_inv_item_indices(ids.JUG))}')
            if attempts >= 5:
                self.log_msg(f'failed attempt')
                break

    def grape_loop(self): 
        if self.api_m.get_is_inv_full():
            return
        item_start_count = len(self.api_m.get_inv_item_indices(ids.GRAPES))
        attempts = 0
        
        while len(self.api_m.get_inv_item_indices(ids.GRAPES)) == item_start_count:
            attempts += 1
            self.log_msg(f'grape attempt {attempts}')
            attempted_to_click = self.attempt_to_click('Grapes', 'Grapes', clr.OFF_ORANGE, clr.PINK, 7, (0, -25))
            self.log_msg(f'initial grapes {item_start_count} new grapes count {len(self.api_m.get_inv_item_indices(ids.GRAPES))}')
            if attempted_to_click:
                time.sleep(self.random_sleep_length(1,3))
            if attempts >= 5:
                self.log_msg(f'failed attempt')
                break
