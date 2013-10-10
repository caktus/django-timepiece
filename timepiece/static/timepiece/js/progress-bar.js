var progressBars = {
	elements: []
	,init:function(selector){
		progressBars.elements = $(selector);
		progressBars.elements.each(function(){
			$(this).append('<div class="over">');
			$(this).append('<div class="worked">');
			$(this).append('<div class="remaining">');
		});
		progressBars.increment();
	}
	,increment:function(){
		$(progressBars.elements).each(function(){
			var worked = Math.min(this.dataset.secondsWorked,this.dataset.secondsAssigned);
			var remaining = Math.max(0,this.dataset.secondsAssigned - this.dataset.secondsWorked);
			var over = Math.max(0,this.dataset.secondsWorked - this.dataset.secondsAssigned);

			$(this).children('.over')
				.attr('style','flex:'+over)
				.text(progressBars.humanizeSeconds(over));
			$(this).children('.worked')
				.attr('style','flex:'+worked)
				.text(progressBars.humanizeSeconds(worked));
			$(this).children('.remaining')
				.attr('style','flex:'+remaining)
				.text(progressBars.humanizeSeconds(remaining));
			// increment
			if( $(this).hasClass('active') ){
				this.dataset.secondsWorked++;
			}
		});
	}
	,humanizeSeconds:function(seconds){
		var minutes = seconds / 60;
		var hours = minutes / 60;
		var days = hours / 8;
		var weeks = days / 5;
		var months = days / 30;
		var years = months / 12;

		//if(years > 2) return Math.floor(years) + ' years';
		//if(months > 2) return Math.floor(months) + ' months';
		//if(weeks > 2) return Math.floor(weeks) + ' weeks';
		//if(days > 2) return Math.floor(days) + ' days';
		if(hours > 2) return Math.floor(hours) + ' hours';
		if(minutes > 2) return Math.floor(minutes) + ' minutes';
		if(seconds > 2) return Math.floor(seconds) + ' seconds';
		return '';
		
	}
};

$(document).ready(function(){
	progressBars.init('.progress-bar');
	setInterval(progressBars.increment,1000);	
});
