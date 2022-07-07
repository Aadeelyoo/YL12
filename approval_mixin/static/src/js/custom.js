odoo.define('approval_mixin.custom', function (require) {
"use strict";

var mailUtils = require('mail.utils');

var AbstractField = require('web.AbstractField');
var BasicModel = require('web.BasicModel');
var core = require('web.core');
var field_registry = require('web.field_registry');
var time = require('web.time');

var QWeb = core.qweb;
var _t = core._t;
var MailActivity = require('mail.Activity');

MailActivity.include({
    init: function () {
        this._super.apply(this, arguments);
        this.events = _.extend(this.events, {
            'click .o_hold_activity': '_onHoldActivity',
            'click .o_reject_activity': '_onRejectActivity',
        });
    },
    // Accept Button Dialog
    _onMarkActivityDoneActions: function ($btn, $form, activityID) {
        var self = this;
        $form.find('#activity_feedback').val(self._draftFeedback[activityID]);
        $form.on('click', '.o_activity_popover_done', function (ev) {
            ev.stopPropagation();
            self._rpc({
                model: 'mail.approvers',
                method: 'update_approver_state',
                args: [[]],
                kwargs: {activity_id: activityID},
                context: {
                    'accept_btn':1,
                },
            }).then(function (result){
                self._markActivityDone({
                    activityID: activityID,
                    feedback: _.escape($form.find('#activity_feedback').val()),
                });
            });
        });
        $form.on('click', '.o_activity_popover_done_next', function (ev) {
            ev.stopPropagation();
            self._markActivityDoneAndScheduleNext({
                activityID: activityID,
                feedback: _.escape($form.find('#activity_feedback').val()),
            });
        });
        $form.on('click', '.o_activity_popover_discard', function (ev) {
            ev.stopPropagation();
            if ($btn.data('bs.popover')) {
                $btn.popover('hide');
            } else if ($btn.data('toggle') == 'collapse') {
                self.$('#o_activity_form_' + activityID).collapse('hide');
            }
        });
        $form.on('click', '.o_activity_popover_test', function (ev) {
            ev.stopPropagation();
            self._rpc({
                model: 'mail.activity.type',
                method: 'print_some_statement',
                args: [self._activities[0].activity_type_id[0]],
            })
        });
    },

    // Hold Button Method
    _onHoldActivity: function (ev, options) {
        ev.preventDefault();
        var self = this;
        var activityID = $(ev.currentTarget).data('activity-id');
        options = _.defaults(options || {}, {
            model: 'mail.activity',
            args: [[activityID]],
        });
        self._rpc({
            model: 'mail.approvers',
            method: 'update_approver_state',
            args: [[]],
            kwargs: {activity_id: activityID},
            context: {
                'hold_btn':1,
            },
        }).then(function (result){
                self._rpc({
                    model: options.model,
                    method: 'action_record_hold',
                    args: options.args,
                })
                

            }).then(this._reload.bind(this, {activity: true}));
    },

    // Reject Button Method
    _onRejectActivity: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var self = this;
        var $markDoneBtn = $(ev.currentTarget);
        var activityID = $markDoneBtn.data('activity-id');
        var previousActivityTypeID = $markDoneBtn.data('previous-activity-type-id') || false;
        var forceNextActivity = $markDoneBtn.data('force-next-activity');

        if ($markDoneBtn.data('toggle') == 'collapse') {
            var $actLi = $markDoneBtn.parents('.o_log_activity');
            var $panel = self.$('#o_activity_form_' + activityID);

            if (!$panel.data('bs.collapse')) {
                var $form = $(QWeb.render('mail.activity_feedback_form_rejection', { previous_activity_type_id: previousActivityTypeID, force_next: forceNextActivity}));
                $panel.append($form);
                self._onMarkActivityRejectDoneActions($markDoneBtn, $form, activityID);

                // Close and reset any other open panels
                _.each($panel.siblings('.o_activity_form'), function (el) {
                    if ($(el).data('bs.collapse')) {
                        $(el).empty().collapse('dispose').removeClass('show');
                    }
                });

                // Scroll  to selected activity
                $markDoneBtn.parents('.o_activity_log_container').scrollTo($actLi.position().top, 100);
            }

            // Empty and reset panel on close
            $panel.on('hidden.bs.collapse', function () {
                if ($panel.data('bs.collapse')) {
                    $actLi.removeClass('o_activity_selected');
                    $panel.collapse('dispose');
                    $panel.empty();
                }
            });

            this.$('.o_activity_selected').removeClass('o_activity_selected');
            $actLi.toggleClass('o_activity_selected');
            $panel.collapse('toggle');

        } else if (!$markDoneBtn.data('bs.popover')) {
            $markDoneBtn.popover({
                template: $(Popover.Default.template).addClass('o_mail_activity_feedback')[0].outerHTML, // Ugly but cannot find another way
                container: $markDoneBtn,
                title : _t("Feedback"),
                html: true,
                trigger:'click',
                placement: 'right', // FIXME: this should work, maybe a bug in the popper lib
                content : function () {
                    var $popover = $(QWeb.render('mail.activity_feedback_form_rejection', { previous_activity_type_id: previousActivityTypeID, force_next: forceNextActivity}));
                    self._onMarkActivityRejectDoneActions($markDoneBtn, $popover, activityID);
                    return $popover;
                },
            }).on('shown.bs.popover', function () {
                var $popover = $($(this).data("bs.popover").tip);
                $(".o_mail_activity_feedback.popover").not($popover).popover("hide");
                $popover.addClass('o_mail_activity_feedback').attr('tabindex', 0);
                $popover.find('#activity_feedback').focus();
                self._bindPopoverFocusout($(this));
            }).popover('show');
        }
    },

    // Reject Button Dialog 
    _onMarkActivityRejectDoneActions: function ($btn, $form, activityID) {
        var self = this;
        $form.find('#activity_feedback_rejection').val(self._draftFeedback[activityID]);
        $form.on('click', '.o_activity_popover_rejection_done', function (ev) {
            ev.stopPropagation();
            self._rpc({
                model: 'mail.approvers',
                method: 'update_approver_state',
                args: [[]],
                kwargs: {activity_id: activityID},
                context: {
                    'reject_btn':1,
                },
            }).then(function (result){
                self._markActivityRejectionDone(ev,{
                    
                    activityID: activityID,
                    feedback: _.escape($form.find('#activity_feedback_rejection').val()),
                });

            });
        });
    },

    // Reject Button Dialog Button DONE 
    _markActivityRejectionDone: function (ev, options) {
        ev.preventDefault();
        var self = this;
        var activityID = $(ev.currentTarget).data('activity-id');

        self._rpc({
            model: 'mail.activity',
            method: 'action_record_reject',
            args: [[options.activityID]],
            kwargs: {feedback: options.feedback},
            context: this.record.getContext(),
        })
        .then(this._reload.bind(this, { activity: true, thread: true }));
    },
    
    // Render Method for updating count  
    _render: function () {
        _.each(this._activities, function (activity) {
            var note = mailUtils.parseAndTransform(activity.note || '', mailUtils.inline);
            var is_blank = (/^\s*$/).test(note);
            if (!is_blank) {
                activity.note = mailUtils.parseAndTransform(activity.note, mailUtils.addLink);
            } else {
                activity.note = '';
            }
        });
        var activities = setDelayLabel(this._activities);
        if (activities.length) {

            var activitiesApproval = []
            var activitiesOther = []
            activities.forEach((activity)=>{
            if(activity.category=='approval'){
            activitiesApproval.push(activity)
            }else {
            activitiesOther.push(activity)
            }
            }
            )
            var nbActivities = _.countBy(activitiesOther, 'state');
            var nbActivitiesOther = _.countBy(activitiesApproval, 'category');
            this.$el.html(QWeb.render('mail.activity_items', {
                activities: activities,
                nbPlannedActivities: nbActivities.planned,
                nbTodayActivities: nbActivities.today,
                nbOverdueActivities: nbActivities.overdue,
                nbApprovalActivities: nbActivitiesOther.approval,
                dateFormat: time.getLangDateFormat(),
                datetimeFormat: time.getLangDatetimeFormat(),
            }));
        } else {
            this.$el.empty();
        }
    },

})


/**
 * Set the 'label_delay' entry in activity data according to the deadline date
 *
 * @param {Array} activities list of activity Object
 * @return {Array} : list of modified activity Object
 */
var setDelayLabel = function (activities){
    var today = moment().startOf('day');
    _.each(activities, function (activity){
        var toDisplay = '';
        var diff = activity.date_deadline.diff(today, 'days', true); // true means no rounding
        if (diff === 0){
            toDisplay = _t("Today");
        } else {
            if (diff < 0){ // overdue
                if (diff === -1){
                    toDisplay = _t("Yesterday");
                } else {
                    toDisplay = _.str.sprintf(_t("%d days overdue"), Math.abs(diff));
                }
            } else { // due
                if (diff === 1){
                    toDisplay = _t("Tomorrow");
                } else {
                    toDisplay = _.str.sprintf(_t("Due in %d days"), Math.abs(diff));
                }
            }
        }
        activity.label_delay = toDisplay;
    });
    return activities;
};
});