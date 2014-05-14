var tables = $('table');
var i;
var navbarHeight = $('.navbar').height();

function recalculateCutoffs(){
	for (i = 0; i < tables.length; i++) {
		tables[i].dataset.top = $(tables[i]).children('thead').offset().top;
		tables[i].dataset.bottom = $(tables[i]).height() - $(tables[i]).children('thead').height() - $(tables[i]).children('tbody tr:last').height();
	}
}
recalculateCutoffs();

function recalculateHeaders(){
	for (i = 0; i < tables.length; i++) {
		difference = $(window).scrollTop() + navbarHeight - tables[i].dataset.top;

		if(difference <= 0){
			tables[i].querySelector('thead').style.webkitTransform = 'translate(0px,0px)';
			tables[i].querySelector('thead').style.MozTransform = 'translate(0px,0px)';
		}
		if(difference > 0){
			tables[i].querySelector('thead').style.webkitTransform = 'translate(0px,'+ difference +'px)';
			tables[i].querySelector('thead').style.MozTransform = 'translate(0px,'+ difference +'px)';
		}
		if(difference > tables[i].dataset.bottom){
			tables[i].querySelector('thead').style.webkitTransform = 'translate(0px,'+ tables[i].dataset.bottom +'px)';
			tables[i].querySelector('thead').style.MozTransform = 'translate(0px,'+ tables[i].dataset.bottom +'px)';
		}
	}
//	console.log( difference );
}
recalculateHeaders();

window.onscroll = function(){ recalculateHeaders(); };
window.onresize = function(){ setTimeout( recalculateCutoffs, 100); recalculateHeaders(); };
