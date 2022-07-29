odoo.define('pivot_view_sticky_freeze_header.pivotview_freeze_header', function (require) {
'use strict';
    var pivot_Renderer = require('web.PivotRenderer');
    var web_Session = require('web.session');

    pivot_Renderer.include({
       _render:function(ev){
           var pivot_super = this._super.apply(this, arguments);
           if(web_Session.pivot_view_state_head){
               this.stick_PivotView(this);
           }
           return pivot_super
        },
        on_attach_callback: function(){
           var pivot_super = this._super.apply(this, arguments);
           var pivot_sticky = this;
           if(web_Session.pivot_view_state_head){
                pivot_sticky.stick_PivotView(pivot_sticky);
           }
           $("div[class='o_sub_menu']").css("z-index",4);
           return pivot_super
        },
        on_detach_callback: function () {
           var pivot_super = this._super.apply(this, arguments);
           var pivot_sticky=this;
           
           if(web_Session.pivot_view_state_head){
               var o_pivot_area = $(".o_pivot")[0];
               var pivot_sticky_el = pivot_sticky.$el;
               if(pivot_sticky_el.parents(".o_dashboard").length===0){
                       pivot_sticky_el.each(function () {
                               $(this).stickyTableHeadersPivot('destroy');
                        });
                }
            }
           return pivot_super
        },
        stick_PivotView:function(el){
           var pivot_sticky=el;
           var o_pivot_area = $(".o_pivot")[0];
           var pivot_sticky_el = pivot_sticky.$el;
           if(pivot_sticky_el.parents(".o_dashboard").length===0){
                   pivot_sticky_el.each(function () {
                           $(this).stickyTableHeadersPivot({scrollableArea: o_pivot_area, fixedOffset: 0.1,stickStatus: web_Session.pivot_view_state_head});
                    });
            }
           this.first_Column_Fixed();
       },
        first_Column_Fixed : function(){
            if(web_Session.pivot_view_state_head){
             _.each($(".o_pivot table tbody .o_pivot_header_cell_opened"), function(pivot_view_cell) {
                    $(pivot_view_cell).css({
                       'left' : '0',
                       'position' : 'sticky'
                    });
                      $(pivot_view_cell).css({
                       'position' : ' -webkit-sticky;'
                    });
               });
                _.each($(".o_pivot table tbody .o_pivot_header_cell_closed"), function(pivot_view_cell) {
                    $(pivot_view_cell).css({
                       'left' : '0',
                       'position' : 'sticky'
                    });
                     $(pivot_view_cell).css({
                       'position' : ' -webkit-sticky'
                    });
               });
         }
         else{
            $(".freeze_row_blur").css({
                "display":"none",
            })
         }

        },
    });
});

