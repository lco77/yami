
// Escape raw output for HTML display
function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

// render a table from an object
function objectToTable(obj, selector) {
  const $table = $('<table class="table table-striped"><tbody></tbody></table>');
  const $tbody = $table.find('tbody');

  for (const [key, value] of Object.entries(obj)) {
    $tbody.append(`<tr><td><p class="text-primary"><b>${key}</b></p></td><td>${value}</td></tr>`);
  }

  $(selector).html($table);
}

// filter and re-map object keys, then return new object
function mapObjectKeys(source, keyMap) {
  const result = {};

  keyMap.forEach(entry => {
    const [srcKey, dstKey] = Object.entries(entry)[0];
    if (srcKey in source) {
      result[dstKey] = source[srcKey];
    }
  });
  
  return result;
}


// convert time strings into seconds
function timeToSeconds(timeStr) {
  // HH:MM:SS format
  if (/^\d{1,2}:\d{1,2}:\d{1,2}$/.test(timeStr)) {
    const [h, m, s] = timeStr.split(':').map(Number);
    return h * 3600 + m * 60 + s;
  }

  // Text format (e.g. 16w1d, 1d04h)
  let total = 0;
  const regex = /(\d+)([wdhms])/g;
  let match;
  while ((match = regex.exec(timeStr)) !== null) {
    const value = parseInt(match[1], 10);
    const unit = match[2];
    switch (unit) {
      case 'w': total += value * 7 * 24 * 3600; break;
      case 'd': total += value * 24 * 3600; break;
      case 'h': total += value * 3600; break;
      case 'm': total += value * 60; break;
      case 's': total += value; break;
    }
  }

  return total;
}
