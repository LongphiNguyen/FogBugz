#This script will print a list of all overdue cases assigned to me

from fogbugz import FogBugz
from datetime import datetime, timedelta
import fbSettings # fbSettings.txt
import pyodbc
from datetime import datetime
from datetime import date
import calendar
import time

# Get FogBugz API connection information
print fbSettings.URL
print fbSettings.TOKEN


# --------------------------------------------------------------
# SECTION: System settings
# --------------------------------------------------------------


SETTINGSFILE='fbSettings.py' # if this changes, also change the "import fbSettings" abvoe
SERVER='PC-Longphi'
DATABASE='FogBugz'

fb = FogBugz(fbSettings.URL, fbSettings.TOKEN)

'''
#Get all cases assigned to me
resp = fb.search(cols='ixBug,sTitle,dtDue')

print 'The following cases are overdue:'

for case in resp.cases.childGenerator():
    #Check to see if we have a due date
    if case.dtdue.string: 
        #All dates returned are UTC, so parse the due date
        #into a datetime object.
        dtDueUtc = datetime.strptime(case.dtdue.string,'%Y-%m-%dT%H:%M:%SZ')
        fOverdue = dtDueUtc <= datetime.utcnow()
        if fOverdue:
            tdDays = (datetime.utcnow() - dtDueUtc).days
            sTitle = case.stitle.string.encode('UTF-8')
            print "%s: %s (%s days)" % (case['ixbug'], sTitle, tdDays)

for case in resp.cases.childGenerator():
    print case['ixbug'] + ':' + case.stitle.string
'''
'''
filters=fb.listFilters()
for filt in filters:
    print(filt)
'''


# --------------------------------------------------------------
# SECTION: Get all recently updated cases and their information.
# --------------------------------------------------------------


query='edited:"' + str(fbSettings.LASTRECORDED) + '..now"'
#query="106265"
#query="105112"
query="106243"
query='edited:today'
# SEARCH for all cases that were recently edited. These are the cases that needs their data updated.
resp=fb.search(q=query, cols='ixBug,sTitle,sProject,sArea,sCategory,ixPersonAssignedTo,sPersonAssignedTo,sPriority,sStatus,dtOpened,dtClosed,ixPersonOpenedBy,ixBugParent,sFixFor,ixPersonResolvedBy,ixPersonClosedBy,dtResolved,dtDue,dtLastUpdated,ixKanban,ixPersonLastEditedBy,hrsElapsed,hrsCurrEst,hrsOrigEst,hrsElapsedExtra,plugin_kanbanboard_at_ergonlabs_com_ixkanbancolumn,plugin_kanbanboard_at_ergonlabs_com_ncolor')#include Kanban to see other Kanban fields (though not useful)
# cols='dtResolved,dtDue,dtLastUpdated,ixPersonLastEditedBy,hrsElapsed,hrsCurrEst,hrsOrigEst,hrsElapsedExtra,Kanban,plugin_kanbanboard_at_ergonlabs_com_ixkanbancolumn,plugin_kanbanboard_at_ergonlabs_com_ncolor'
#resp=fb.search(q="kanban:1",cols='ixBug,sTitle,dtResolved,dtDue,dtLastUpdated,ixKanban,ixPersonLastEditedBy,hrsElapsed,hrsCurrEst,hrsOrigEst,hrsElapsedExtra', max=2)
#print resp.prettify()

minID=0
maxID=2000
step=100

PersonsList = {}
insertValues = [] # values to insert into dbo.Case
insertDates = set() # values to insert into dbo.TimeTable
caseXML=[]

# class for cases, to improve readability
class Case:
    def __init__(self):
        # case info
        self.IDCase = 0
        self.IDParentCase = 0
        self.Title = ""
        self.Status = ""
        self.Project = ""
        self.Area = ""
        self.Category = ""
        self.Priority = ""
        self.Milestone = ""
        # people and IDS
        self.IDAssignedTo = 0
        self.AssignedTo = ""
        self.IDOpenedBy = 0
        self.OpenedBy = ""
        self.IDResolvedBy = 0
        self.ResolvedBy = ""
        self.IDClosedBy = 0
        self.ClosedBy = ""
        self.IDLastEditedBy = 0
        self.LastEditedBy = ""
        # dates
        self.OpenedDate = None
        self.ClosedDate = None
        self.ResolvedDate = None
        self.DueDate = None
        self.LastUpdatedDate = None
        # hours
        self.hrsElapsed = 0.00
        self.hrsCurrEst = 0.00
        self.hrsOrigEst = 0.00
        self.hrsElapsedExtra = 0.00
        # kanban
        self.IDKanban = 0
        self.IDKanbanColor = 0
    
    def returnInfo(self):
        return (self.IDCase, self.IDParentCase, self.Title, self.Status, self.Project, self.Area, self.Category, self.Priority, self.Milestone,
                self.IDAssignedTo, self.AssignedTo, self.IDOpenedBy, self.OpenedBy, self.IDResolvedBy, self.ResolvedBy, self.IDClosedBy,
                self.ClosedBy, self.IDLastEditedBy, self.LastEditedBy, self.OpenedDate, self.ClosedDate, self.ResolvedDate, self.DueDate,
                self.LastUpdatedDate, self.hrsElapsed, self.hrsCurrEst, self.hrsOrigEst, self.hrsElapsedExtra, self.IDKanban, self.IDKanbanColor)

# requires PersonsList = {} to be defined in parent scope
def insertToSQL(localminID, localmaxID, PersonsList):
    "Go through case=minID to case=maxID and get their attributes. Then insert those values into the database."
    # Now iterate from minID to maxID
    insertValues = [] # values to insert into dbo.Case
    insertDates = set() # values to insert into dbo.TimeTable
    caseNumbers = ','.join([str(s) for s in range(localminID, localmaxID+1)])
    #for i in range(localminID,localmaxID+1):
    #    case=fb.search(q="case:"+str(i), cols='ixBug,sTitle,sProject,sArea,sCategory,sPersonAssignedTo,sPriority,sStatus,dtOpened,dtClosed')

    # --------------------------
    # defining functions to be used
    # --------------------------
    def getUserName(userID):
        if userID == '0' or userID == '-1':
            return None, None
        else:
            if userID in PersonsList:
                return userID, PersonsList[userID]
            else:
                print 'userID: ' + str(userID)
                person = fb.viewPerson(ixPerson=userID)
                if person.sfullname is None: # no name returned
                    return None, None
                PersonsList[userID] = userName = person.sfullname.string
                return userID, userName

    # formatDt(dt) takes in a date string (case.dt.string) and formats it to be inserted into dbo.Case. Also places the date into insertDates set to be inserted into dbo.Time
    def formatDt(dt):
        if dt is not None:
            formatted=datetime.strptime(dt,'%Y-%m-%dT%H:%M:%SZ')
            insertDates.update([formatted.strftime('%Y%m%d')])

            #if formatted > maxDate:
                #maxDate=formatted
            return formatted
        else:
            return None
    
    resp=fb.search(q=caseNumbers, cols='ixBug,sTitle,sProject,sArea,sCategory,ixPersonAssignedTo,sPersonAssignedTo,sPriority,sStatus,dtOpened,dtClosed,ixPersonOpenedBy,ixBugParent,sFixFor,ixPersonResolvedBy,ixPersonClosedBy,dtResolved,dtDue,dtLastUpdated,ixKanban,ixPersonLastEditedBy,hrsElapsed,hrsCurrEst,hrsOrigEst,hrsElapsedExtra,plugin_kanbanboard_at_ergonlabs_com_ixkanbancolumn,plugin_kanbanboard_at_ergonlabs_com_ncolor')#include Kanban to see other Kanban fields (though not useful)
    for case in resp.cases.childGenerator():
        CaseObj = Case()
        CaseObj.IDCase = case['ixbug']
        # ----------
        # user name stuff
        # ----------
        print CaseObj.IDCase
        # get Opened By user
        CaseObj.IDOpenedBy, CaseObj.OpenedBy = getUserName(case.ixpersonopenedby.string)
        # get Resolved By user
        CaseObj.IDResolvedBy, CaseObj.ResolvedBy = getUserName(case.ixpersonresolvedby.string)
        # get Closed By user
        CaseObj.IDClosedBy, CaseObj.ClosedBy = getUserName(case.ixpersonclosedby.string)
        # get Last Edited By user
        CaseObj.IDLastEditedBy, CaseObj.LastEditedBy = getUserName(case.ixpersonlasteditedby.string)
        # get Assigned To user
        CaseObj.IDAssignedTo = case.ixpersonassignedto.string
        CaseObj.AssignedTo = case.spersonassignedto.string # oddly, this is the only name that can be obtained directly from the query

        # ----------
        # date stuff
        # ----------

        # get Date Opened
        CaseObj.OpenedDate = formatDt(case.dtopened.string)
        # get Date Closed
        CaseObj.ClosedDate = formatDt(case.dtclosed.string)
        # get Date Resolved
        CaseObj.ResolvedDate = formatDt(case.dtresolved.string)
        # get Date Due
        CaseObj.DueDate = formatDt(case.dtdue.string)
        # get Last Updated
        CaseObj.LastUpdatedDate = formatDt(case.dtlastupdated.string)

        # ----------
        # other info
        # ----------
        
        # get Parent Case
        StrParentCase = case.ixbugparent.string
        if StrParentCase == '0':
            StrParentCase = None
        CaseObj.IDParentCase = StrParentCase
        
        # Kanban
        CaseObj.IDKanban= case.plugin_kanbanboard_at_ergonlabs_com_ixkanbancolumn.string
        CaseObj.IDKanbanColor= case.plugin_kanbanboard_at_ergonlabs_com_ncolor.string

        # hours elapsed, estimated, original, extra
        CaseObj.hrsElapsed = case.hrselapsed.string#round(float(case.hrselapsed.string),3)
        CaseObj.hrsCurrEst = case.hrscurrest.string#round(float(case.hrscurrest.string),3)
        CaseObj.hrsOrigEst = case.hrsorigest.string#round(float(case.hrsorigest.string),3)
        CaseObj.hrsElapsedExtra = case.hrselapsedextra.string#round(float(case.hrselapsedextra.string),3)

        # (StrKanban)
        CaseObj.Title = case.stitle.string
        CaseObj.Status = case.sstatus.string
        CaseObj.Project = case.sproject.string
        CaseObj.Area = case.sarea.string
        CaseObj.Category = case.scategory.string
        CaseObj.Priority = case.spriority.string
        CaseObj.Milestone = case.sfixfor.string
        
        # return the values as a tuple, ordered as in Case.returnInfo()
        insertValues.append(CaseObj.returnInfo())

        if CaseObj.IDResolvedBy is None and CaseObj.ResolvedBy is not None:
            caseXML.append(case)
    return PersonsList;

respOpened = fb.listCases(sFilter="1056", cols='ixBug')#,sTitle,sProject,sArea,sCategory,sPersonAssignedTo,sPriority,sStatus,dtOpened,dtClosed')
# get max ID
maxID=0
for case in respOpened.cases.childGenerator():
    if case['ixbug']>maxID:
        maxID=case['ixbug']

maxID=2000

PersonsList = {}
minID=0
step=4999 # 1-10000, 10001-20000, etc
while True:
    if minID+step < maxID:
        print "LOOKING AT CASES: " + str(minID) + " to " + str(minID+step) + ", stopping at " + str(maxID) 
        PersonsList = insertToSQL(minID, minID+step, PersonsList)
        minID=minID+step+1
    else:
        PersonsList = insertToSQL(minID, maxID, PersonsList)
        print "LOOKING AT CASES: " + str(minID) + " to " + str(maxID)
        minID=maxID
        break
    time.sleep(5)

# --------------------------------------
resp=fb.search(q=query, cols='ixBug,sTitle,sProject,sArea,sCategory,ixPersonAssignedTo,sPersonAssignedTo,sPriority,sStatus,dtOpened,dtClosed,ixPersonOpenedBy,ixBugParent,sFixFor,ixPersonResolvedBy,ixPersonClosedBy,dtResolved,dtDue,dtLastUpdated,ixKanban,ixPersonLastEditedBy,hrsElapsed,hrsCurrEst,hrsOrigEst,hrsElapsedExtra,plugin_kanbanboard_at_ergonlabs_com_ixkanbancolumn,plugin_kanbanboard_at_ergonlabs_com_ncolor')#include Kanban to see other Kanban fields (though not useful)
for case in resp.cases.childGenerator():
    CaseObj = Case()
    CaseObj.IDCase = case['ixbug']
    # ----------
    # user name stuff
    # ----------
    print CaseObj.IDCase
    # get Opened By user
    CaseObj.IDOpenedBy, CaseObj.OpenedBy = getUserName(case.ixpersonopenedby.string)
    # get Resolved By user
    CaseObj.IDResolvedBy, CaseObj.ResolvedBy = getUserName(case.ixpersonresolvedby.string)
    # get Closed By user
    CaseObj.IDClosedBy, CaseObj.ClosedBy = getUserName(case.ixpersonclosedby.string)
    # get Last Edited By user
    CaseObj.IDLastEditedBy, CaseObj.LastEditedBy = getUserName(case.ixpersonlasteditedby.string)
    # get Assigned To user
    CaseObj.IDAssignedTo = case.ixpersonassignedto.string
    CaseObj.AssignedTo = case.spersonassignedto.string # oddly, this is the only name that can be obtained directly from the query

    # ----------
    # date stuff
    # ----------

    # get Date Opened
    CaseObj.OpenedDate = formatDt(case.dtopened.string)
    # get Date Closed
    CaseObj.ClosedDate = formatDt(case.dtclosed.string)
    # get Date Resolved
    CaseObj.ResolvedDate = formatDt(case.dtresolved.string)
    # get Date Due
    CaseObj.DueDate = formatDt(case.dtdue.string)
    # get Last Updated
    CaseObj.LastUpdatedDate = formatDt(case.dtlastupdated.string)

    # ----------
    # other info
    # ----------
    
    # get Parent Case
    StrParentCase = case.ixbugparent.string
    if StrParentCase == '0':
        StrParentCase = None
    CaseObj.IDParentCase = StrParentCase
    
    # Kanban
    CaseObj.IDKanban= case.plugin_kanbanboard_at_ergonlabs_com_ixkanbancolumn.string
    CaseObj.IDKanbanColor= case.plugin_kanbanboard_at_ergonlabs_com_ncolor.string

    # hours elapsed, estimated, original, extra
    CaseObj.hrsElapsed = case.hrselapsed.string#round(float(case.hrselapsed.string),3)
    CaseObj.hrsCurrEst = case.hrscurrest.string#round(float(case.hrscurrest.string),3)
    CaseObj.hrsOrigEst = case.hrsorigest.string#round(float(case.hrsorigest.string),3)
    CaseObj.hrsElapsedExtra = case.hrselapsedextra.string#round(float(case.hrselapsedextra.string),3)

    # (StrKanban)
    CaseObj.Title = case.stitle.string
    CaseObj.Status = case.sstatus.string
    CaseObj.Project = case.sproject.string
    CaseObj.Area = case.sarea.string
    CaseObj.Category = case.scategory.string
    CaseObj.Priority = case.spriority.string
    CaseObj.Milestone = case.sfixfor.string
    
    # return the values as a tuple, ordered as in Case.returnInfo()
    insertValues.append(CaseObj.returnInfo())

    if CaseObj.IDResolvedBy is None and CaseObj.ResolvedBy is not None:
        caseXML.append(case)

# --------------------------------------
def test():
    temp = set()
    def testinner(i):
        if i==1 or i==3:
            temp.update([i])
            return i
        else:
            return None
    for i in range(0,4):
        testinner(i)
    print temp
    return None

# test()

def test2():
    return (1,2)

a,b=test2()
#print a
#print b

testList = []
testList.append((1,2,
                 3))
#print testList

class testClass():
    def __init__(self):
        self.ID = None
        self.Title = None

a=testClass()
a.ID=123
#print a.ID
