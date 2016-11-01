/*
 * Project Ginger Base
 *
 * Copyright IBM Corp, 2015-2016
 *
 * Code derived from Project Kimchi
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
gingerbase.repository_edit_main = function() {

    var editForm = $('#form-repository-edit');
    var saveButton = $('#repository-edit-button-save');

    if(gingerbase.capabilities['repo_mngt_tool']=="yum") {
        editForm.find('div.deb').hide();
    }
    else if(gingerbase.capabilities['repo_mngt_tool']=="deb") {
        editForm.find('div.yum').hide();
    }

    gingerbase.retrieveRepository(gingerbase.selectedRepository, function(repository) {
        editForm.fillWithObject(repository);

        $('input', editForm).on('input propertychange', function(event) {
            if($(this).val() !== '') {
                $(saveButton).prop('disabled', false);
            }
        });
    });


    var editRepository = function(event) {
        var formData = $(editForm).serializeObject();

        if (formData && formData.config) {
            formData.config.gpgcheck=(String(formData.config.gpgcheck).toLowerCase() === 'true');
        }

        if(formData.config && formData.config.comps) {
            formData.config.comps=formData.config.comps.split(/[,\s]/);
            for(var i=0; i>formData.config.comps.length; i++) {
                formData.config.comps[i]=formData.config.comps[i].trim();
            }
            for (var j=formData.config.comps.indexOf(""); j!=-1; j=formData.config.comps.indexOf("")) {
                formData.config.comps.splice(j, 1);
            }
        }

        gingerbase.updateRepository(gingerbase.selectedRepository, formData, function() {
            wok.topic('gingerbase/repositoryUpdated').publish();
            $("#repositories-grid-enable-button").attr('disabled', true);
            $("#repositories-grid-edit-button").attr('disabled', true);
            $("#repositories-grid-remove-button").attr('disabled', true);
            wok.window.close();
        }, function(jqXHR, textStatus, errorThrown) {
            var reason = jqXHR &&
                jqXHR['responseJSON'] &&
                jqXHR['responseJSON']['reason'];
            wok.message.error(reason, '#alert-modal-container');
        });

        return false;
    };

    $(editForm).on('submit', editRepository);
    $(saveButton).on('click', editRepository);
};
