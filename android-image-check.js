var DEBUG = false;

var print = function(str){
    console.log(str);
}

var debug = function(str){
    if (DEBUG){
        print(str);
    }
}

debug('Starting...');

var page = require('webpage').create();
var url = 'https://developers.google.com/android/nexus/images';

phantom.cookiesEnabled = true;
phantom.addCookie({
	'name':	'NID',
	'value': '!! GET THIS COOKIE VALUE FROM YOUR OWN SESSION !!',
	'domain': '.google.com'
});

/* Suck up any errors, and only print them if in debug */
page.onError = function(msg, trace) {
    var msgStack = ['ERROR: ' + msg];
    if (trace && trace.length) {
        msgStack.push('TRACE:');
        trace.forEach(function(t) {
            msgStack.push(' -> ' + t.file + ': ' + t.line + (t.function ? ' (in function "' + t.function + '")' : ''));
        });
    }
    // uncomment to log into the console
    // console.error(msgStack.join('\n'));
    debug(msgStack.join('\n'));
};

page.open(url, function(status) {
    if (status === 'fail') {
        console.log('Failed to get page');
    } else {
        page.render('test.png');
        var data = page.evaluate(function() {
			if ( $('.devsite-acknowledgement-link').is(':visible') ){
				console.log('Seeing the TOS link, quitting');
				phantom.exit();
			}

            //return document.querySelector('tr[id^="bullhead"]').innerText
            return { version: $('tr[id^="bullhead"]').last().attr('id'), text: $('tr[id^="bullhead"]').last().html() };
        })
        debug(JSON.stringify(data))
        if (data.version !== 'bullheadnmf26f'){
            console.log('New Version:');
            console.log(data.text);
		}
        phantom.exit();
    }
});

