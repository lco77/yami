
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
    $alert.show()
}

// close alert
function close_alert() {
    $("#alert").hide();
}

// API get
function get(url, params = {}) {
    // Build query string from params
    const query = new URLSearchParams(params).toString();
    const fullUrl = query ? `${url}?${query}` : url;

    return fetch(fullUrl, {
        method: "GET",
        headers: {
            "Content-Type": "application/json"
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error("GET request failed:", error);
            throw error;
        });
}

// API post
function post(url, params = {}, data = {}) {
    // Build query string from params
    const query = new URLSearchParams(params).toString();
    const fullUrl = query ? `${url}?${query}` : url;

    return fetch(fullUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: Object.keys(data).length ? JSON.stringify(data) : null
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error("GET request failed:", error);
            throw error;
        });
}

// Resolve a DNS name
// Usage:
// resolve_hostname("example.com").then(ip => {
//     if (ip) {
//       alert("IP Address: " + ip);
//     } else {
//       alert("Failed to resolve hostname.");
//     }
//   });
function resolve_hostname(name) {
    return fetch("/resolve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.ip) {
        return data.ip;
      } else {
        return null;
      }
    })
    .catch(error => {
      return null;
    });
  }

// Start a background task
function createTask(url, type, data) {
    return fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            type: type,
            data: data
        })
    })
        .then(res => res.json())
        .then(data => data.task_id || null)
        .catch(err => {
            console.error("Task creation failed:", err);
            return null;
        });
}

// Poll a background task
function pollTask(getTaskUrl, taskId, pollInterval, statusSelector) {
    return new Promise((resolve, reject) => {
        const pollUrl = getTaskUrl.replace("DUMMY", taskId);
        const poll = setInterval(() => {
            fetch(pollUrl)
                .then(res => res.json())
                .then(task => {
                    if (task.status === "SUCCESS") {
                        clearInterval(poll);
                        if (task.success) {
                            resolve(task.result);
                        } else {
                            reject("Task failed");
                        }
                    } else if (task.status === "FAILURE") {
                        clearInterval(poll);
                        reject("Task failed");
                    }
                })
                .catch(err => {
                    clearInterval(poll);
                    reject("Error checking task: " + err);
                });
        }, pollInterval);
    });
}



// runTasks - sequential
async function runTasksSeq(tasks) {
    const updatedTasks = [];
  
    for (const task of tasks) {
      const taskCopy = { ...task };
  
      try {
        const taskId = await createTask(createTaskUrl, task.type, task.params);
  
        if (!taskId) {
          taskCopy.result = { success: false, error: "Task creation failed" };
        } else {
          const taskResult = await pollTask(getTaskUrl, taskId, pollInterval);
          taskCopy.result = taskResult;
        }
      } catch (error) {
        taskCopy.result = { success: false, error: String(error) };
      }
  

  
      updatedTasks.push(taskCopy);
    }
  
    return updatedTasks;
  }

// runTasks - parallel
async function runTasks(tasks) {
  const promises = tasks.map(async (task) => {
    const taskCopy = { ...task };

    try {
      const taskId = await createTask(createTaskUrl, task.type, task.params);

      if (!taskId) {
        taskCopy.result = { success: false, error: "Task creation failed" };
      } else {
        const taskResult = await pollTask(getTaskUrl, taskId, pollInterval);
        taskCopy.result = taskResult;
      }
    } catch (error) {
      taskCopy.result = { success: false, error: String(error) };
    }

    return taskCopy;
  });

  // Wait for all tasks to complete
  return Promise.all(promises);
}
