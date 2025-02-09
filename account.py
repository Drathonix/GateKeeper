from swipe import Swipe
from python_freeipa import ClientMeta
import logging
from config import Config

ONE_USER_MATCHED = '1 user matched'

class Account():
    """
    Representation of an IPA server account.
    """

    def __init__(self, swipe: Swipe, client: ClientMeta, logger: logging.Logger, config: Config) -> None:
        self.logger = logger
        self.config = config
        self.client = client
        self.user = client.user_find(o_employeenumber=swipe.id) # returns a dictionary with the user's info
        self.summary = self.get_summary()
        self.swiped_lcc = swipe.lcc
        self.id = swipe.id

        try:
            self.netid = self.get_net_id()
            self.lcc = self.get_lcc()
            self.groups = self.get_groups()
            self.has_access = self.has_access()
        except Exception as e:
            self.has_access = False

    def get_net_id(self) -> str:
        return self.user['result'][0]['uid'][0]
    
    def get_summary(self) -> str:
        return self.user['summary']
    
    def get_lcc(self) -> str:
        return self.user['result'][0]['employeetype'][0]
    
    def get_groups(self) -> list:
        return self.user['result'][0]['memberof_group']
    
    def has_access(self) -> bool:
        """
        Returns `True` if the user should have access 
        based on their credentials. Returns `False` if
        they are denied access. 
        """
        
        if self.summary != ONE_USER_MATCHED:
            # make sure that there is only one user being matched
            # (if swiped lcc and 8 digit num are both empty, all users will be matched)
            return False

        if not (set(self.groups) & self.config.access.allowed_groups):
            # account does not have any of the groups with access
            return False
        
        try:
            if int(self.swiped_lcc) < int(self.lcc):
                # if someone tries to swipe with an earlier, 
                # perhaps lost id, access will be denied
                self.logger.warning(f"LCC of user {self.netid} is {self.lcc}. Swiped LCC was {self.swiped_lcc}.")
                return False
            elif int(self.swiped_lcc) > int(self.lcc):
                # if someone tries to swipe with a newer lcc id,
                # update their lcc in Citadel and grant access
                self.logger.info(f"LCC of user {self.netid} is {self.lcc}. Swiped LCC was {self.swiped_lcc}. Updating user {self.netid} with new LCC of {self.swiped_lcc}...")

                try:
                    self.update_LCC()
                    self.logger.info(f"The LCC change for user {self.netid} from {self.lcc} to {self.swiped_lcc} succeeded.")
                except Exception as e:
                    self.logger.warning(f"The attempt to change the LCC of user {self.netid} from {self.lcc} to {self.swiped_lcc} failed.")
                    self.logger.exception(e)
        except:
            self.logger.warning("LCC String to Int conversion failed. Automatically denying access.")
            return False

        return True
    
    def update_LCC(self) -> None:
        """
        Updates the LCC of the user to the LCC thatwas swiped.
        """
        
        self.client.user_mod(a_uid=self.netid, o_employeetype=self.swiped_lcc)
