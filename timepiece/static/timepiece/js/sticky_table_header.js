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
			thead.style.webkitTransform = 'translate(0px,'+ difference_top +'px)';
			thead.style.MozTransform = 'translate(0px,'+ difference_top +'px)';
		}
		if(difference_top > table.dataset.bottom){
			thead.style.webkitTransform = 'translate(0px,'+ table.dataset.bottom +'px)';
			thead.style.MozTransform = 'translate(0px,'+ table.dataset.bottom +'px)';
		}
	}

	function calculateColumnCutoffs(table){
		table.dataset.left = $(table).find('tr td:first').offset().left;
	}

	function positionColumns(scrollContainer){
		var difference_left = $(scrollContainer).scrollLeft();
		var table = scrollContainer.querySelector('table');

		if(difference_left <= 0){
			$(table).find('tbody tr > :first-child').css('WebkitTransform', 'translate(0px,0px)');
			$(table).find('tbody tr > :first-child').css('MozTransform', 'translate(0px,0px)');
		}
		if(difference_left > 0){
			$(table).find('tbody tr > :first-child').css('WebkitTransform', 'translate('+ difference_left +'px, 0px)');
			$(table).find('tbody tr > :first-child').css('MozTransform', 'translate('+ difference_left +'px, 0px)');
		}
	}

	for (i = 0; i < tables.length; i++) {
		// attach x scroll event to container
		$(tables[i]).parent().on('scroll', function(){ positionColumns(this); });
		// init positions
		calculateColumnCutoffs(tables[i]);
		calculateHeaderCutoffs(tables[i]);
		positionHeaders(tables[i]);
		positionColumns(tables[i]);
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
			calculateColumnCutoffs(tables[i]);
			calculateHeaderCutoffs(tables[i]);
			positionHeaders(tables[i]);
		}
	};
};

stickyHeader();
