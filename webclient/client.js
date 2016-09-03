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

// Log messages from the server
connection.onmessage = function (e) {
  var response = JSON.parse(e.data);
  console.log('Server: ' + e.data);

    switch(response.type) {
	case "start": channelboard.channelStart(response.freq); break;
	case "stop":  channelboard.channelStop(response.freq); break;
	case "tune":  channelboard.channelTag(response.freq, response.tg); break;
    };

};
