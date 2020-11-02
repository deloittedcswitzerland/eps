// Class to make callout and send params to einstein-prediction-service
public class einsteinCallout {
    @future(callout=true)
	public static void makePostCallout(String caseId) {	
    	EmailMessage emailMessage = [SELECT Id, HasAttachment FROM EmailMessage WHERE RelatedToId=:caseId LIMIT 1];
        IF (emailMessage.HasAttachment) {
            Http http = new Http();
            string body = 'image=' + caseId;
            System.debug(body);
            HttpRequest request = new HttpRequest();
            request.setEndpoint('https://einstein-prediction-service.herokuapp.com/post/');
            request.setMethod('POST');
    
            // Set the body as a JSON object
            request.setBody(body);
            HttpResponse response = http.send(request);
            System.debug(response.getBody());
            // Parse the JSON response
            if (response.getStatusCode() != 201) {
                System.debug('The status code returned was not expected: ' +
                response.getStatusCode() + ' ' + response.getStatus());
                System.debug(request.getBody());
            } else {
                System.debug(response.getBody());
            }
            System.debug(request.getBody());
        } else {}
    }
}