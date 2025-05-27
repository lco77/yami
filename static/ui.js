
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