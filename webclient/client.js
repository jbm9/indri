var hostname = "52.43.230.29", // document.location.hostname, // XXX TODO
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

  if (response.type != "click") { return; }

  var a = response.sender.split("-");
  var freq = a[0];
  var status = a[1];

  switch(status) {
      case "start":  channelboard.channelStart(freq); break;
      case "stop": channelboard.channelStop(freq); break;
      
  };

};
