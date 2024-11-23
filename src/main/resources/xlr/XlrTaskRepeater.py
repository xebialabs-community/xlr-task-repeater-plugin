#
# Copyright 2024 XEBIALABS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

# properties common to all tasks to be added:
# taskType
# taskTitle
# taskTitleDiscriminator
# taskPropertyNameForConnection
# taskConnectionType
# taskConnectionName
# taskConnectionId
# taskPropertyNameForSecret
# taskSecret

# list of properties specific to a single task to be added:
# taskProperties

import json

def get_connection(connection_type, connection_name, connection_search_folder_id, connection_search_folder_only, connection_id):
    if not (connection_type or connection_name or connection_id):
        return None
    if (connection_type or connection_name) and connection_id:
        raise Exception("Specify either connection name and type or connection id.")
    if connection_id:
        connection = configurationApi.getConfiguration(connection_id)
        if connection:
            return connection
        else:
            raise Exception("Connection %s not found" % connection_id)
    connection_list = configurationApi.searchByTypeAndTitle(connection_type, connection_name, connection_search_folder_id, connection_search_folder_only,)
    if len(connection_list) == 1:
        return connection_list[0]
    else:
        raise Exception("%s matches found for connection with type %s and name %s" % (["No", "Multiple"][len(connection_list) and 1], connection_type, connection_name))

def set_connection(target_object, property_name, connection):
    target_object.setProperty(property_name, connection)

def is_password_property(target_object, property_name):
    input_properties = target_object._delegate.getInputProperties()
    for p in input_properties:
        if p.name == property_name and p.isPassword():
            return True
    return False

def set_secret(target_object, property_name, secret):
    if is_password_property(target_object, property_name):
        target_object.setProperty(property_name, secret)
    else:
        raise Exception("Cannot set secret value in non-password property %s" % property_name)

def set_gate_dependencies(gate_task, dependencies):
    for d in dependencies:
        taskApi.addDependency(gate_task.id, d['targetId'])

def set_properties(target_object, task_properties_as_json, task_type):
    for key in task_properties_as_json:
        if type(task_properties_as_json[key]) is list:
            if key == 'dependencies' and task_type == 'xlrelease.GateTask':
                set_gate_dependencies(target_object, task_properties_as_json[key])
            else:
                if target_object.hasProperty(key):
                    target_object.setProperty(key, [json.dumps(item).strip('"') for item in task_properties_as_json[key]])
                else:
                    print "Warning: Ignoring input key %s because task type %s does not have property %s" % (key, task_type, key)
        else:
            if target_object.hasProperty(key):
                target_object.setProperty(key, task_properties_as_json[key])
            else:
                print "Warning: Ignoring input key %s because task type %s does not have property %s" % (key, task_type, key)

def get_task_index(p_container, p_task):
    for i, t in enumerate(p_container.tasks):
        if t.id == p_task.id:
            return i
    return None

def apply_task_title_discriminator(title, discriminator, properties_json):
    value = properties_json
    parts = discriminator.split('.')
    for part in parts:
        if type(value) is list:
            if part.isdigit():
                value = value[int(part)]
            else:
                raise Exception("List index must be a positive integer")
        else:
            value = value[part]
    return "%s %s" % (title, value)

print "Executing xlr/XlrTaskRepeater.py v@project.version@"

connection = get_connection(taskConnectionType, taskConnectionName, taskConnectionSearchFolderId, taskConnectionSearchFolderOnly, taskConnectionId)

this_task = getCurrentTask()
this_container = this_task.getContainer()

target_container_id = None
insert_position = None

if str(insertGroup) == 'PARALLEL':
    par_group = taskApi.newTask("xlrelease.ParallelGroup")
    par_group.title = "%s parallel group" % taskTitle
    par_group = phaseApi.addTask(this_container.id, par_group, get_task_index(this_container, this_task) + insertAfter + 1)
    target_container_id = par_group.id
    insert_position = 0

if str(insertGroup) == 'SEQUENTIAL':
    seq_group = taskApi.newTask("xlrelease.SequentialGroup")
    seq_group.title = "%s sequential group" % taskTitle
    seq_group = phaseApi.addTask(this_container.id, seq_group, get_task_index(this_container, this_task) + insertAfter + 1)
    target_container_id = seq_group.id
    insert_position = 0

if str(insertGroup).upper() == 'NONE':
    target_container_id = this_container.id
    insert_position = get_task_index(this_container, this_task) + insertAfter + 1

for idx, entry in enumerate(taskProperties):
    task_properties_as_json = json.loads(entry)
    new_task = taskApi.newTask(taskType)
    if taskTitleDiscriminator:
        new_task.title = apply_task_title_discriminator(taskTitle, taskTitleDiscriminator, task_properties_as_json)
    else:
        new_task.title = "%s %d" % (taskTitle, idx + 1)
    new_task = phaseApi.addTask(target_container_id, new_task, insert_position + idx)
    python_script = None
    if new_task.hasProperty('pythonScript'):
        python_script = new_task.getProperty('pythonScript')
    if taskPropertyNameForConnection and connection:
        set_connection(python_script or new_task, taskPropertyNameForConnection, connection)
    if taskPropertyNameForSecret and taskSecret:
        set_secret(python_script or new_task, taskPropertyNameForSecret, taskSecret)
    set_properties(python_script or new_task, task_properties_as_json, taskType)
    taskApi.updateTask(new_task.id, new_task)

print "Task repeater has completed successfully."
