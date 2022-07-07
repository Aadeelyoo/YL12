odoo.define('dashboard_widgets.dashboard', function (require) {
    "use strict";

    var KanbanRecord = require('web.KanbanRecord');

    KanbanRecord.include({

        _render: function () {
            var self = this;
            var res = this._super();
            window._w = this;
            if(self.modelName == "is.dashboard.widget" &&
                self.recordData["play_sound_on_change_down"] && self.recordData['play_sound_on_change_down_url'] &&
                self.recordData["play_sound_on_change_up"] && self.recordData['play_sound_on_change_up_url']){
                var play_sound_on_change_down = self.recordData["play_sound_on_change_down"];
                var play_sound_on_change_up = self.recordData["play_sound_on_change_up"];
                var sound_down_file_url = self.recordData["play_sound_on_change_down_url"];
                var sound_up_file_url = self.recordData["play_sound_on_change_up_url"];
                var current_value = self.recordData['count_display'];
                var last = self.get_last_value();

                if (last === undefined || last === null){
                    self.set_last_value(current_value);
                } else {
                    self.set_last_value(current_value);
                    if (play_sound_on_change_down && current_value < last){
                        self.play_sound(sound_down_file_url);
                    } else if (play_sound_on_change_up && current_value > last){
                        self.play_sound(sound_up_file_url);
                    }
                }
            }
            return res;
        },
        get_last_value: function(){
            return localStorage.getItem('widget-' + this.id);
        },
        set_last_value: function(value){
            localStorage.setItem('widget-' + this.id, value);

        },
        play_sound: function(file_url){
            var x = document.createElement("AUDIO");
            x.setAttribute('autoplay', 'autoplay')
            x.setAttribute('src', file_url);
            x.play();
        },
    });
});
