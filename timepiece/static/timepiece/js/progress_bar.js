var progressBars = {
	elements: []
	,init:function(){
		progressBars.elements = document.querySelectorAll(".progress-bar");;
		progressBars.increment();
	}
	,getSubDocument:function(embedding_element){
		if (embedding_element.contentDocument) {
			return embedding_element.contentDocument;
		}else{
			var subdoc = null;
			try {
				subdoc = embedding_element.getSVGDocument();
			} catch(e) {}
			return subdoc;
		}
	}
	,increment:function(){
		for (var i=0; i < progressBars.elements.length; i++){
			this_elem = progressBars.elements[i];
			var scheduled = this_elem.dataset.secondsAssigned;
			var worked = Math.min(this_elem.dataset.secondsWorked,this_elem.dataset.secondsAssigned);
			var remaining = Math.max(0,this_elem.dataset.secondsAssigned - this_elem.dataset.secondsWorked);
			var over = Math.max(0,this_elem.dataset.secondsWorked - this_elem.dataset.secondsAssigned);

			var svg = this_elem.querySelector('svg');
            var svg_id = '#progress-' + i;

			svg.querySelector(svg_id + " rect").setAttribute('width', worked/scheduled*100+'%');
			if( $(this_elem).hasClass('humanize') ){
				var time_worked = {
					hours: progressBars.toStandardHumanized(worked)
					,minutes:''
					,seconds:''
				};
				var time_remaining = {
					hours: progressBars.toStandardHumanized(remaining)
					,minutes:''
					,seconds:''
				};
				var separator = '';
			}else{
				var time_worked = progressBars.toStandardClock(worked);
				var time_remaining = progressBars.toStandardClock(remaining);
				var separator = ':';
			}

			svg.querySelector('.unfilled .worked .hours').textContent = time_worked.hours;
			svg.querySelector('.unfilled .worked .minutes').textContent = separator+time_worked.minutes;
			svg.querySelector('.unfilled .worked .seconds').textContent = separator+time_worked.seconds;
			svg.querySelector('.filled .worked .hours').textContent = time_worked.hours;
			svg.querySelector('.filled .worked .minutes').textContent = separator+time_worked.minutes;
			svg.querySelector('.filled .worked .seconds').textContent = separator+time_worked.seconds;
			
			svg.querySelector('.unfilled .remaining .hours').textContent = time_remaining.hours;
			svg.querySelector('.unfilled .remaining .minutes').textContent = separator+time_remaining.minutes;
			svg.querySelector('.unfilled .remaining .seconds').textContent = separator+time_remaining.seconds;
			svg.querySelector('.filled .remaining .hours').textContent = time_remaining.hours;
			svg.querySelector('.filled .remaining .minutes').textContent = separator+time_remaining.minutes;
			svg.querySelector('.filled .remaining .seconds').textContent = separator+time_remaining.seconds;
			
			// increment
			if( $(this_elem).hasClass('active') ){
				this_elem.dataset.secondsWorked++;
			}
		}
	}
	,toWorkHumanized:function(seconds){
		var minutes = seconds / 60;
		var hours = minutes / 60;
		var days = hours / 8;
		var weeks = days / 5;
		var months = days / 30;
		var years = months / 12;

		if(years >= 2) return Math.floor(years) + ' workyears';
		if(months >= 2) return Math.floor(months) + ' workmonths';
		if(weeks >= 2) return Math.floor(weeks) + ' workweeks';
		if(days >= 2) return Math.floor(days) + ' workdays';
		if(hours >= 2) return Math.floor(hours) + ' workhours';
		if(minutes >= 2) return Math.floor(minutes) + ' workminutes';
		if(seconds >= 2) return Math.floor(seconds) + ' workseconds';
		return '';
		
	}
	,toStandardHumanized:function(seconds){
		var minutes = seconds / 60;
		var hours = minutes / 60;
		var days = hours / 24;
		var weeks = days / 7;
		var months = days / 30.4;
		var years = days / 365.24;

		if(years >= 2) return Math.floor(years) + ' years';
		if(months >= 2) return Math.floor(months) + ' months';
		if(weeks >= 2) return Math.floor(weeks) + ' weeks';
		if(days >= 2) return Math.floor(days) + ' days';
		if(hours >= 2) return Math.floor(hours) + ' hours';
		if(minutes >= 2) return Math.floor(minutes) + ' minutes';
		if(seconds >= 2) return Math.floor(seconds) + ' seconds';
		return '';
		
	}
	,toStandardClock:function(seconds){
		var minutes = seconds / 60;
		var hours = minutes / 60;

		var output = {};
			output.hours = Math.floor(hours);
			output.minutes = Math.floor( minutes - output.hours*60 );
			output.seconds = Math.floor( seconds - output.hours*3600 - output.minutes*60 );

		return output;
	}
	,pad:function(n, width, z) {
		z = z || '0';
		n = n + '';
		return n.length >= width ? n : new Array(width - n.length + 1).join(z) + n;
	}
};

$(document).ready(function(){
	// FIXME There is a race between the Document of the embedded svgs and the page embedding them.
    progressBars.init();
	setInterval(progressBars.increment,1000);	
});
