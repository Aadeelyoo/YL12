odoo.define('approval_mixin.mail_chatter', function (require) {
"use strict";

var Activity = require('mail.Activity');
var AttachmentBox = require('mail.AttachmentBox');
var ChatterComposer = require('mail.composer.Chatter');
var Dialog = require('web.Dialog');
var Followers = require('mail.Followers');
var ThreadField = require('mail.ThreadField');
var mailUtils = require('mail.utils');

var concurrency = require('web.concurrency');
var config = require('web.config');
var core = require('web.core');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;

var MailChatter = require('mail.Chatter');

MailChatter.include({
	init: function () {
		this._super.apply(this, arguments);
		this.adobe_agreement_id = 0;
		this.adobe_agreement_semi_view_id = 0;
		this.events = _.extend(this.events, {
			'click .o_play_btn': '_onPlayButton',
			'click .o_pause_btn': '_onPauseButton',
			'click .o_stop_btn': '_onStopButton',
			'click .o_approvers_btn': '_onApproversButton',
			'click .o_sign_events_btn': '_onSignEventsButton',
		});
	},

	start: function () {
		var self = this;
		this._updateApproverCounter(this.record);
		// self._rpc({
		// 		model: 'mail.approval',
		// 		method: 'custom_search_count',
		// 		args: [[]],
		// 		kwargs: {res_id: self.record.data.id, res_model: self.context.default_model},
		// 	}).then(function(result){
		// 		if (result.total_count > 0) {
		// 			self.$('.btn-left').append(QWeb.render('mail.approvers_action_button', {}));
		// 		}
		// 	});

		return this._super.apply(this, arguments);
	},

	/**
	 * @param {Object} record
	 * @param {integer} [record.res_id=undefined]
	 * @param {Object[]} [fieldNames=undefined]
	 */
	update: function (record, fieldNames) {
		var self = this;
		if (this.record.res_id !== record.res_id) {
			this._updateApproverCounter(record);
		}
		else{
			this._updateApproverCounter(this.record);
		}
		return this._super.apply(this, arguments);
	},


	// Play Button Method
	_onPlayButton: function (ev) {
		ev.preventDefault();
		var self = this;
		var PlayBtn = $(ev.currentTarget);
		var context = self.context
		self._rpc({
			model: 'mail.approvers',
			method: 'action_mail_approval_start',
			args: [[]],
			context: context,
		}).then(function (result){
			self.trigger_up('reload');
		});
	},

	// Pause Button Method
	_onPauseButton: function (ev) {
		ev.preventDefault();
		var self = this;
		var PauseBtn = $(ev.currentTarget);
		var context = self.context
		self._rpc({
			model: 'mail.approvers',
			method: 'action_mail_approval_pause',
			args: [[]],
			context: context,
		}).then(function (result){
			self.trigger_up('reload');
		});
	},

	// Stop Button Method
	_onStopButton: function (ev) {
		ev.preventDefault();
		var self = this;
		var StopBtn = $(ev.currentTarget);
		var context = self.context
		self._rpc({
			model: 'mail.approvers',
			method: 'action_mail_approval_stop',
			args: [[]],
			context: context,
		}).then(function (result){
			self.trigger_up('reload');
		});
	},

	// Sign Events Button Method
	_onSignEventsButton: function (ev) {
		ev.preventDefault();
		var self = this;
		var ApproverBtn = $(ev.currentTarget);
		var res_id = self.context.default_res_id;
		var res_model = self.context.default_model;
		if (this.adobe_agreement_id > 0) {
            self.do_action({
                type: 'ir.actions.act_window',
                res_model: 'adobe.agreement',
                res_id: this.adobe_agreement_id,
                name: "Sign Events",
                views: [[this.adobe_agreement_semi_view_id, 'form']],
                target:'new',
                flags: {mode: 'readonly'},
            }, { on_close: function () {
                self.trigger_up('reload');
            }});
		}


	},
	// Approvers Button Method
	_onApproversButton: function (ev) {
		ev.preventDefault();
		var self = this;
		var ApproverBtn = $(ev.currentTarget);
		var res_id = self.context.default_res_id;
		var res_model = self.context.default_model;
		self.do_action({
			type: 'ir.actions.act_window',
			res_model: 'mail.approvers',
			res_id: self.id,
			domain:[['res_id','=',res_id],['res_model','=',res_model]],
			context: {
				'res_id': res_id,
				'res_model':res_model,
				'default_res_id': res_id,
				'default_res_model':res_model,
			},
			views: [ [false, 'list']],
			target:'new',
		});

	},

	/**
	 * @private
	 */
	 _updateApproverCounter: function (record) {
		var self = this;
		var res_id = record.data.id;

		var res_model = self.context.default_model;
		var $element_approved_count = this.$('.mail_approver_count_approved');
		var $element_rejected_count = this.$('.mail_approver_count_rejected');
		var $element_total_count = this.$('.mail_approver_count');
		var $element_sign_events_count = this.$('.adobe_sign_event_count');

		if (res_id){

			self._rpc({
					model: 'adobe.agreement',
					method: 'acquire_agreement_information',
					args: [[]],
					kwargs: {res_id: res_id, res_model: res_model},
				}).then(function(result){
					var events_count = result.events_count || 0;

                    if (result.agreement_id) {
                        self.$('.o_sign_events_btn').show()
                        self.adobe_agreement_id = result.agreement_id;
                        self.adobe_agreement_semi_view_id = result.agreement_view_id;
                        if (Number($element_sign_events_count.html()) !== events_count) {
                            $element_sign_events_count.html(events_count);
                        }
                    } else {
                        self.$('.o_sign_events_btn').hide()
                    }
				});

			self._rpc({
					model: 'mail.approval',
					method: 'custom_search_count',
					args: [[]],
					kwargs: {res_id: res_id, res_model: res_model},
				}).then(function(result){
					var approved_count = result.approved_count || 0;
					var rejected_count = result.rejected_count || 0;
					var total_count = result.total_count || 0;
					
					if (Number($element_approved_count.html()) !== approved_count) {
						$element_approved_count.html(approved_count);
					}
					
					if (Number($element_rejected_count.html()) !== rejected_count) {
						$element_rejected_count.html(rejected_count);
					}

					if (Number($element_total_count.html()) !== total_count) {
						$element_total_count.html(total_count);
					}
				});
		}
	 },

})


});