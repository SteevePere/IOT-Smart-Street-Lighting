
  //LEAFLET

  var map = L.map('map').setView([48.8126508,2.3881197], 15);
  var layer = L.tileLayer('http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png', {
  });

  var i = 0
  var lat = 0
  var lng = 0

  map.on('click', onMapClick);

  function onMapClick(e) {
    if (i == 0) {
      marker = new L.marker(e.latlng, {draggable:'true'});
      var position = marker.getLatLng();
      console.log(position.lat, position.lng)

      marker.on('dragend', function(event){
        var marker = event.target;
        var position = marker.getLatLng();
        marker.setLatLng(new L.LatLng(position.lat, position.lng),{draggable:'true'});
        map.panTo(new L.LatLng(position.lat, position.lng))
        lat = position.lat
        long = position.lng
        console.log(position.lat, position.lng)
      });
      map.addLayer(marker);
      i = 1
      lat = position.lat
      long = position.lng
    }
  };

  map.addLayer(layer);

  $(document).ready( function() {
        $('#submit').click(function() {
            var street = $('#street').find(":selected").text();
            var newStreet = $('#streetInput').val();
            if (street == "Choisir une Rue...") {
                $("#streetAlert").fadeTo(1500, 500).slideUp(500, function(){
                $("#streetAlert").slideUp(500);
              });
              return;
            } else if (street == "Ajouter une Rue...") {
              if (!newStreet) {
                $("#newStreetAlert").fadeTo(1500, 500).slideUp(500, function(){
                  $("#newStreetAlert").slideUp(500);
                });
                return;
              } else {
                street = newStreet
              }
            }
            try {
              $.post(
                "/newDevice",
                { lat: lat, long: long, street: street }
             ).done(function (reply) {
                $('#reply').empty().append(reply);
                $("#successAlert").fadeTo(1500, 500).slideUp(500, function(){
                  $("#successAlert").slideUp(500);
                  location.reload()
                });
             });
           }
           catch (err) {
             $("#geolocAlert").fadeTo(1500, 500).slideUp(500, function(){
               $("#geolocAlert").slideUp(500);
             });
           }
        });
        $('#street').change(function() {

          var street = $('#street').find(":selected").text();
          var streetInput = document.getElementById("streetInput");

          if (street == "Ajouter une Rue...") {
            if (streetInput.style.display === "none") {
              streetInput.style.display = "block";
            }
          }
          else {
            if (streetInput.style.display === "block") {
              streetInput.style.display = "none";
            }
          }
        });
  });
