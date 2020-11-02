// Trigger to pass caseId to einsteinCallout class
trigger einsteinCaseTrigger on Case (after insert) {
    for(Case c : Trigger.New) {
        string caseId = c.Id;
        einsteinCallout.makePostCallout(caseId); 
    }   
}