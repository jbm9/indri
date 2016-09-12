var hostname = document.location.hostname, // XXX TODO
    connection = new WebSocket('ws://' + hostname + ':8081/'),
    count,
    msg = {
      console: $('#event-console'),
      log: function(message) {
        var log = $('<div class="event-msg"></div>');
        log.html(message).prependTo(msg.console);
      },
      installed_list: $('#installed-modules'),
      install: function(name, url) {
        msg.installed_list.append('<li><a href="' + url + '">' + name + '</a></li>');
      }
    };

// When the connection is open, send some data to the server
connection.onopen = function () {
  connection.send('Ping'); // Send the message 'Ping' to the server
};

// Log errors
connection.onerror = function (error) {
  console.log('WebSocket Error ' + error);
};

var tg_follow = [ 0x3270, 0x3290 ];

function handle_tgfile(response) {
	  if ((-1 == tg_follow) || (-1 != tg_follow.indexOf(parseInt(response.tg))))
	      scanner_player.enqueue(response.tg, response.path);
//	else
//	    console.log("No hit on tg=" + parseInt(response.tg));
}

function handle_fileup(response) {
    scanner_player.available(response.path);
}

// Log messages from the server
connection.onmessage = function (e) {
  var response = JSON.parse(e.data);
    // console.log('Server: ' + e.data);

    switch(response.type) {
	case "start": channelboard.channelStart(response.freq); break;
	case "stop":  channelboard.channelStop(response.freq); break;
	case "tune":  channelboard.channelTag(response.freq, response.tg); break;
	case "tgfile": handle_tgfile(response); break;
	case "fileup": handle_fileup(response); break;
          break;
	case "connected":
	   var dump = response.states;
	   for (var i = 0; i < dump.length; i++) {
	       var cs = dump[i];

	       if (cs.state == "open") {
		   channelboard.channelStart(cs.freq);
		   if (cs.tg != 0) channelboard.channelTag(cs.freq, cs.tg);
	       } else if(cs.state == "closed") {
		   channelboard.channelStop(cs.freq);
	       }
	   }
    };

};
