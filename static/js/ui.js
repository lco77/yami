
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

// Function to Format Bitrate
function formatBitrate(bps) {
    bps = Number(bps); // Ensure it's a number
    if (isNaN(bps)) return "Invalid";

    if (bps >= 1e9) {
        return (bps / 1e9).toFixed(2) + " gb/s";
    } else if (bps >= 1e6) {
        return (bps / 1e6).toFixed(2) + " mb/s";
    } else if (bps >= 1e3) {
        return (bps / 1e3).toFixed(2) + " kb/s";
    } else {
        return bps + " b/s";
    }
}

// convert short interface name to its full length
function interface_name(val) {
    const prefixMap = {
        Fa: "FastEthernet",
        Bl: "Bluetooth",
        Po: "Port-channel",
        Lo: "Loopback",
        Hu: "HundredGigE",
        Gi: "GigabitEthernet",
        Te: "TenGigabitEthernet",
        Twe: "TwentyFiveGigE",
        Vl: "Vlan"
    };
    for (const [prefix, replacement] of Object.entries(prefixMap)) {
        if (val.startsWith(prefix)) {
            val = val.replace(prefix, replacement);
            break;
        }
    }
    return val;
};

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

    function parse_port(line, portCol, nameCol) {
        let val = line.substring(portCol, nameCol).trim();
        return interface_name(val);
    };

    for (const line of lines) {
        const interface = parse_port(line, portCol, nameCol)
        const description = line.substring(nameCol, downCol).trim();
        const downTime = line.substring(downCol, upCol).trim();
        const upTime = line.substring(upCol).trim();

        data.push({
            interface: interface,
            description: description,
            downtime: downTime,
            downtime_seconds: timeToSeconds(downTime),
            uptime: upTime,
            uptime_seconds: timeToSeconds(upTime)
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
        <div class="form-group col-2" >
            <label for="parentSelector" class="form-label">Monitor Type</label>
            <select id="parentSelector" class="form-select"></select>
        </div>

        <div class="form-group col-2">
            <label for="actionSelector" class="form-label">Data Set</label>
            <select id="actionSelector" class="form-select"></select>
        </div>

        <!-- Dynamic filter fields will be injected here -->
        <div id="dynamicFilters" class="d-flex gap-3 flex-wrap"></div>

        <!-- Submit button aligned to far right -->
        <div class="col-lg-1">
            <button id="submitAction" class="btn btn-success form-control">Submit</button>
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

        show_alert('info', 'Hang on', 'Fetching realtime data...');
        post(url, {}, payload).then(monitorData => {
            // Extract column definitions dynamically
            const monitorColumns = monitorData.header.columns.map(col => {
                const base = {
                    data: col.property,
                    title: col.title || col.property,
                    defaultContent: ''
                };
                if (col.dataType === 'date' && col.inputFormat === 'unix-time') {
                    base.render = function (data) {
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
        }).catch(error => {
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

// parse vlan data
function parseVlanData(arrayShInt, arrayShIntSwitchport, arrayShSpaVlan, vlanId = null) {

    function parseTrunkVlans(trunkingVlans) {
        const vlanSet = new Set();
        trunkingVlans.forEach(entry => {
            entry.split(',').forEach(part => {
                if (part.includes('-')) {
                    const [start, end] = part.split('-').map(Number);
                    for (let i = start; i <= end; i++) {
                        vlanSet.add(i.toString());
                    }
                } else if (part.trim().toUpperCase() === "ALL") {
                    for (let i = 1; i <= 4094; i++) {
                        vlanSet.add(i.toString());
                    }
                } else {
                    vlanSet.add(part.trim());
                }
            });
        });
        return Array.from(vlanSet);
    }

    function summarizeVlans(vlans) {
        if (vlans.length >= 4094) return "ALL";

        const nums = vlans.map(Number).sort((a, b) => a - b);
        const ranges = [];

        let start = nums[0];
        let end = nums[0];

        for (let i = 1; i < nums.length; i++) {
            if (nums[i] === end + 1) {
                end = nums[i];
            } else {
                if (start === end) {
                    ranges.push(start.toString());
                } else {
                    ranges.push(`${start}-${end}`);
                }
                start = end = nums[i];
            }
        }

        // Push the final range
        if (start === end) {
            ranges.push(start.toString());
        } else {
            ranges.push(`${start}-${end}`);
        }

        return ranges.join(',');
    }

    const switchportMap = {};
    arrayShIntSwitchport.forEach(entry => {
        switchportMap[interface_name(entry.interface)] = entry;
    });

    const stpMap = {};
    arrayShSpaVlan.forEach(entry => {
        const key = `${interface_name(entry.interface)}::${entry.vlan_id}`;
        stpMap[key] = entry;
    });

    return arrayShInt.map(intf => {
        const iface = intf.interface;
        const spData = switchportMap[iface] || {};
        const mode = spData.mode === "trunk" ? "trunk" : "access";

        let vlanList = [];
        if (mode === "access") {
            vlanList = [spData.access_vlan || spData.native_vlan].filter(Boolean);
        } else {
            vlanList = parseTrunkVlans(spData.trunking_vlans || []);
        }

        if (vlanId && !vlanList.includes(vlanId)) {
            return null;
        }

        const stpKey = `${iface}::${vlanId || vlanList[0]}`;
        const stpEntry = stpMap[stpKey] || {};

        return {
            interface: iface,
            description: intf.description || "",
            status: intf.link_status === "up" ? "up" : "down",
            mode: mode,
            vlans: vlanList,
            vlans_str: summarizeVlans(vlanList),
            port_id: stpEntry.port_id || "",
            stp_cost: stpEntry.cost || "",
            stp_priority: stpEntry.port_id || "",
            stp_role: stpEntry.role || "",
            stp_status: stpEntry.status || "",
            stp_type: stpEntry.type?.trim() || ""
        };
    }).filter(Boolean); // Remove null entries
}

// Parse Meraki networks
function transformNetworks(networks, templates) {
    // Build lookup map from template ID to template object
    const templateMap = Object.fromEntries(templates.map(t => [t.id, t]));

    return networks.map(net => {
        const isTemplateBased = net.raw_data.isBoundToConfigTemplate;
        const templateId = isTemplateBased ? net.raw_data.configTemplateId : null;
        const template = templateId ? templateMap[templateId] : null;

        return {
            id: net.id,
            template_id: templateId,
            template_name: template ? template.name : null,
            name: net.name,
            url: net.url,
            notes: net.raw_data.notes || null,
            type: net.raw_data.productTypes || [],
            tags: net.raw_data.tags || []
        };
    });
}

// Meraki: render badges from a list of tags
function buildBadgeMapFromTags(data) {
    const colors = [
        "primary", "secondary", "success",
        "danger", "warning", "info", "light", "dark"
    ];

    // Step 1: Collect all tags
    const tagSet = new Set();
    data.forEach(item => {
        if (Array.isArray(item.tags)) {
            item.tags.forEach(tag => tagSet.add(tag));
        }
    });

    // Step 2: Sort tags alphabetically
    const sortedTags = Array.from(tagSet).sort((a, b) => a.localeCompare(b));

    // Step 3: Assign colors and build map
    const badgeMap = {};
    let lastColorIndex = -1;

    for (let i = 0; i < sortedTags.length; i++) {
        let colorIndex = (lastColorIndex + 1) % colors.length;

        // Ensure no adjacent same color
        if (colorIndex === lastColorIndex && colors.length > 1) {
            colorIndex = (colorIndex + 1) % colors.length;
        }

        const color = colors[colorIndex];
        lastColorIndex = colorIndex;

        const tag = sortedTags[i];
        badgeMap[tag] = `<span class="badge bg-${color} me-1">${tag}</span>`;
    }

    return badgeMap;
}