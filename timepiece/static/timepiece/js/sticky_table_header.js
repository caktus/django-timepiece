var tables = $('table');
var i, navbarHeight;

function calculateNavbar(){
	if( window.innerWidth >= 840){
		navbarHeight = $('.navbar').height();
	}else{
		navbarHeight = 0;
	}
}
calculateNavbar();

function calculateHeaderCutoffs(){
	for (i = 0; i < tables.length; i++) {
		tables[i].querySelector('thead').style.webkitTransform = 'translate(0px,0px)';
		tables[i].querySelector('thead').style.MozTransform = 'translate(0px,0px)';
		tables[i].dataset.top = parseInt( $(tables[i]).children('thead').offset().top );
		tables[i].dataset.bottom = parseInt( $(tables[i]).height() - $(tables[i]).children('thead').height() - $(tables[i]).children('tbody tr:last').height() );
	}
}
calculateHeaderCutoffs();

function positionHeaders(){
	for (i = 0; i < tables.length; i++) {
		var scroll = document.documentElement.scrollTop || document.body.scrollTop;
		var difference_top = scroll + navbarHeight - tables[i].dataset.top;

		if(difference_top <= 0){
			tables[i].querySelector('thead').style.webkitTransform = 'translate(0px,0px)';
			tables[i].querySelector('thead').style.MozTransform = 'translate(0px,0px)';
		}
		if(difference_top > 0){
			tables[i].querySelector('thead').style.webkitTransform = 'translate(0px,'+ difference_top +'px)';
			tables[i].querySelector('thead').style.MozTransform = 'translate(0px,'+ difference_top +'px)';
		}
		if(difference_top > tables[i].dataset.bottom){
			tables[i].querySelector('thead').style.webkitTransform = 'translate(0px,'+ tables[i].dataset.bottom +'px)';
			tables[i].querySelector('thead').style.MozTransform = 'translate(0px,'+ tables[i].dataset.bottom +'px)';
		}
	}
}
positionHeaders();

function calculateColumnCutoffs(){
	for (i = 0; i < tables.length; i++) {
		tables[i].dataset.left = $(tables[i]).find('tr td:first').offset().left;
	}
}
calculateColumnCutoffs();

function positionColumns(){
	for (i = 0; i < tables.length; i++) {
		var difference_left = $(tables[i]).parent().scrollLeft();// - tables[i].dataset.left;

		if(difference_left <= 0){
			$(tables[i]).find('tbody tr > :first-child').css('WebkitTransform', 'translate(0px,0px)');
			$(tables[i]).find('tbody tr > :first-child').css('MozTransform', 'translate(0px,0px)');
		}
		if(difference_left > 0){
			$(tables[i]).find('tbody tr > :first-child').css('WebkitTransform', 'translate('+ difference_left +'px, 0px)');
			$(tables[i]).find('tbody tr > :first-child').css('MozTransform', 'translate('+ difference_left +'px, 0px)');
		}
	}
}
positionColumns();

for (i = 0; i < tables.length; i++) {
	$(tables[i]).parent('.scroll-x-axis').on('scroll', function(){ positionColumns(); });
}

window.onscroll = function(){ positionHeaders(); };
window.onresize = function(){
	calculateNavbar();
	calculateColumnCutoffs();
	calculateHeaderCutoffs();
	positionHeaders();
};
