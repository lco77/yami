function showLanDeviceSummary(data,selector) {
    //let html = '<table class="table table-bordered table-sm">';
    let html = '<table class="table table-striped">';
    html += '<thead><tr><th>Key</th><th>Value</th></tr></thead><tbody>';
  
    for (const [key, value] of Object.entries(data)) {
      html += `<tr><td>${key}</td><td>${value}</td></tr>`;
    }
  
    html += '</tbody></table>';
  
    $(selector).html(html);
}