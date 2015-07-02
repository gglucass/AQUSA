$(document).ready(function() {
  $('.edit').editable(window.location.pathname + '/stories/update_story', {
    method: 'POST',
    callback: function(value, settings) {
      window.location.reload();
    }
  });
});