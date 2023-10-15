from swipe import Swipe
from python_freeipa import ClientMeta
import logging

ONE_USER_MATCHED = '1 user matched'

class Account():
    def __init__(self, swipe: Swipe, client: ClientMeta, logger: logging.Logger) -> None:
        self.logger = logger
        self.client = client
        self.user = client.user_find(o_employeenumber=swipe.id) # returns a dictionary with the user's info
        self.summary = self.getSummary()
        self.swiped_lcc = swipe.lcc

        try:
            self.netid = self.getNetID()
            self.lcc = self.getLCC()
            self.groups = self.getGroups()
            self.has_access = self.hasAccess()
        except Exception as e:
            self.has_access = False

    def getNetID(self) -> str:
        return self.user['result'][0]['uid'][0]
    
    def getSummary(self) -> str:
        return self.user['summary']
    
    def getLCC(self) -> str:
        return self.user['result'][0]['employeetype'][0]
    
    def getGroups(self) -> list:
        return self.user['result'][0]['memberof_group']
    
    def hasAccess(self) -> bool:
        if self.summary != ONE_USER_MATCHED:
            # make sure that there is only one user being matched
            # (if swiped lcc and 8 digit num are both empty, all users will be matched)
            return False

        if 'users' not in self.groups:
            # make sure the account is in the users group
            return False
        
        try:
            if int(self.swiped_lcc) < int(self.lcc):
                # if someone tries to swipe with an earlier, 
                # perhaps lost id, access will be denied
                return False
            elif int(self.swiped_lcc) > int(self.lcc):
                # if someone tries to swipe with a newer lcc id,
                # update their lcc in Citadel and grant access
                self.logger.info(f"LCC of user {self.netid} is {self.lcc}. Swiped LCC was {self.swiped_lcc}. Updating user {self.netid} with new LCC of {self.swiped_lcc}...")

                try:
                    self.updateLCC()
                    self.logger.info(f"The LCC change for user {self.netid} from {self.lcc} to {self.swiped_lcc} succeeded.")
                except Exception as e:
                    self.logger.warning(f"The attempt to change the LCC of user {self.netid} from {self.lcc} to {self.swiped_lcc} failed.")
                    self.logger.exception(e)
        except:
            self.logger.warning("LCC String to Int conversion failed. Automatically denying access.")
            return False

        return True
    
    def updateLCC():
        #TODO
        pass
