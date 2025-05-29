
// show
function show(id) {
    $(id).show();
}

// hide
function hide(id) {
    $(id).hide();
}

// show alert
function show_alert(level, title, message) {
    const $alert = $("#alert");

    // Reset and apply new Bootstrap alert class
    $alert
        .removeClass()
        .addClass(`alert alert-dismissible alert-${level}`);

    // Update content
    $alert.find(".alert-heading").text(title);
    $alert.find("p").html(message);

    // Show alert
    $alert.show().addClass('show');
}

// close alert
function close_alert() {
    $("#alert").hide();
}

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

function renderDynamicForm(categories, containerId, monitorTableId, url, deviceId, datatable) {
    const $container = $(containerId);
    $container.empty();

    const formHtml = `
    <br>
    <form id="filterForm" class="d-flex flex-wrap align-items-end gap-3 mb-3">
        <div class="form-group">
            <label for="parentSelector" class="form-label">Monit</label>
            <select id="parentSelector" class="form-select"></select>
        </div>

        <div class="form-group">
            <label for="actionSelector" class="form-label">Sub-Type</label>
            <select id="actionSelector" class="form-select"></select>
        </div>

        <!-- Dynamic filter fields will be injected here -->
        <div id="dynamicFilters" class="d-flex gap-3 flex-wrap"></div>

        <!-- Submit button aligned to far right -->
        <div class="ms-auto">
            <button id="submitAction" class="btn btn-success">Submit</button>
        </div>
    </form>
`;

    $container.html(formHtml);

    // Populate parent categories
    const $parentSelector = $('#parentSelector');
    categories.forEach((cat, index) => {
        $parentSelector.append(`<option value="${index}">${cat.name}</option>`);
    });

    // Update actions when parent changes
    $parentSelector.on('change', function () {
        const parentIndex = $(this).val();
        updateActionSelector(categories[parentIndex].children || []);
    });

    function updateActionSelector(children) {
        const $actionSelector = $('#actionSelector');
        $actionSelector.empty();
        children.forEach((child, idx) => {
            $actionSelector.append(`<option value="${idx}">${child.name}</option>`);
        });

        $actionSelector.off('change').on('change', function () {
            const actionIndex = $(this).val();
            const selectedParent = categories[$('#parentSelector').val()];
            const selectedAction = selectedParent.children[actionIndex];
            renderFilterFields(selectedAction['filter-fields'] || []);
        });

        $actionSelector.trigger('change');
    }

    // Trigger initial population
    $parentSelector.trigger('change');

    // Submit handler with reset
    $(document).off('click', '#submitAction').on('click', '#submitAction', function (e) {
        e.preventDefault();

        const parentIndex = $('#parentSelector').val();
        const actionIndex = $('#actionSelector').val();
        const selectedParent = categories[parentIndex];
        const selectedAction = selectedParent.children[actionIndex];

        const payload = {
            deviceId: deviceId,
            parent: selectedParent.name,
            uri: selectedAction.uri,
            action: selectedAction.name,
            filters: {}
        };

        $('#filterForm').serializeArray().forEach(item => {
            if (item.value.trim() !== '') {
                payload.filters[item.name] = item.value;
            }
        });

        show_alert('info','Hang on', 'Fetching realtime data...');
        post(url,{},payload).then(monitorData=>{
          // Extract column definitions dynamically
          const monitorColumns = monitorData.header.columns.map(col => {
              const base = {
                  data: col.property,
                  title: col.title || col.property,
                  defaultContent: ''
              };
              if (col.dataType === 'date' && col.inputFormat === 'unix-time') {
                  base.render = function(data) {
                      if (!data) return '';
                      const date = new Date(data); // convert seconds to date
                      return date.toLocaleString();
                  };
              }
              return base;
          });
          // reset datatable
          if ($.fn.DataTable.isDataTable(monitorTableId)) {
              $(monitorTableId).DataTable().destroy();
          }
          $(monitorTableId).empty();  // clear headers too
          $(monitorTableId).DataTable({
              layout: {
                  topStart: 'search',
                  topEnd: { buttons: ['pageLength', 'copy', 'excel', 'csv'] }
              },
              ordering: false,
              pageLength: 10,
              fixedHeader: true,
              data: monitorData.data,
              columns: monitorColumns
          });
          close_alert();
        }).catch(error=>{
          show_alert('danger', 'Error', 'Failed to get realtime data.');
        })

    });
}

function renderFilterFields(fields) {
    const $container = $('#dynamicFilters');
    $container.empty();

    fields.forEach(field => {
        const label = field.displayName || field.name;
        const type = field.validation?.type || 'text';

        let inputType = 'text';
        if (type === 'number') inputType = 'number';
        else if (type.startsWith('ipv4')) inputType = 'text';

        const inputHtml = `
            <div class="form-group">
                <label class="form-label">${label}</label>
                <input type="${inputType}" name="${field.name}" class="form-control" />
            </div>
        `;
        $container.append(inputHtml);
    });
}
