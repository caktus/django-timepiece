var stickyHeader = function(){
	var tables = $('table');
	var i, navbarHeight, scroll;

	function calculateNavbar(){
		if( window.innerWidth >= 840){
			navbarHeight = $('.navbar').height();
		}else{
			navbarHeight = 0;
		}
	}
	calculateNavbar();

	function calculateHeaderCutoffs(table){
		table.querySelector('thead').style.webkitTransform = 'translate(0px,0px)';
		table.querySelector('thead').style.MozTransform = 'translate(0px,0px)';
		table.dataset.top = parseInt( $(table).children('thead').offset().top, 10 );
		table.dataset.bottom = parseInt( $(table).height() - $(tables[i]).children('thead').height() - $(tables[i]).children('tbody tr:last').height(), 10 );
	}

	function positionHeaders(table){
		var difference_top = scroll + navbarHeight - table.dataset.top;
		var thead = table.querySelector('thead');
		if(difference_top <= 0){
			thead.style.webkitTransform = 'translate(0px,0px)';
			thead.style.MozTransform = 'translate(0px,0px)';
		}
		if(difference_top > 0){
			if(table.id == 'schedule'){
				thead.style.webkitTransform = 'translate(0px,'+ (difference_top -1) +'px)';
				thead.style.MozTransform = 'translate(0px,'+ (difference_top -1)  +'px)';
			}else{
				thead.style.webkitTransform = 'translate(0px,'+ (difference_top - 7) +'px)';
				thead.style.MozTransform = 'translate(0px,'+ (difference_top -7) +'px)';
			}
		}
		if(difference_top > table.dataset.bottom){
			thead.style.webkitTransform = 'translate(0px,'+ table.dataset.bottom +'px)';
			thead.style.MozTransform = 'translate(0px,'+ table.dataset.bottom +'px)';
		}
	}


	for (i = 0; i < tables.length; i++) {
		calculateHeaderCutoffs(tables[i]);
		positionHeaders(tables[i]);
	}

	window.onscroll = function(){
		for (i = 0; i < tables.length; i++) {
			scroll = document.documentElement.scrollTop || document.body.scrollTop;
			positionHeaders(tables[i]);
		}
	};
	window.onresize = function(){
		calculateNavbar();
		for (i = 0; i < tables.length; i++) {
			calculateHeaderCutoffs(tables[i]);
			positionHeaders(tables[i]);
		}
	};
};

stickyHeader();
