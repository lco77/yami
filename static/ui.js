
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
  const regex = /(\d+)([ywdhms])/g;
  let match;
  while ((match = regex.exec(timeStr)) !== null) {
    const value = parseInt(match[1], 10);
    const unit = match[2];
    switch (unit) {
      case 'y': total += value * 52 * 7 * 24 * 3600; break;
      case 'w': total += value * 7 * 24 * 3600; break;
      case 'd': total += value * 24 * 3600; break;
      case 'h': total += value * 3600; break;
      case 'm': total += value * 60; break;
      case 's': total += value; break;
    }
  }

  return total;
}

//parse "show int link" output
function parseShIntLink(rawText) {
  const lines = rawText.trim().split('\n');

  // Remove the header line and grab column positions from it
  const headerLine = lines.shift();
  const portCol = headerLine.indexOf('Port');
  const nameCol = headerLine.indexOf('Name');
  const downCol = headerLine.indexOf('Down Time');
  const upCol = headerLine.indexOf('Up Time');

  const data = [];

  for (const line of lines) {
    const port = line.substring(portCol, nameCol).trim();
    const name = line.substring(nameCol, downCol).trim();
    const downTime = line.substring(downCol, upCol).trim();
    const upTime = line.substring(upCol).trim();

    data.push({
      port,
      name,
      down_time: downTime,
      up_time: upTime
    });
  }

  return data;
}
