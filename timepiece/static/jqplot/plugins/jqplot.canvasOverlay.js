/**
 * jqPlot
 * Pure JavaScript plotting plugin using jQuery
 *
 * Version: 1.0.0a_r701
 *
 * Copyright (c) 2009-2011 Chris Leonello
 * jqPlot is currently available for use in all personal or commercial projects 
 * under both the MIT (http://www.opensource.org/licenses/mit-license.php) and GPL 
 * version 2.0 (http://www.gnu.org/licenses/gpl-2.0.html) licenses. This means that you can 
 * choose the license that best suits your project and use it accordingly. 
 *
 * Although not required, the author would appreciate an email letting him 
 * know of any substantial use of jqPlot.  You can reach the author at: 
 * chris at jqplot dot com or see http://www.jqplot.com/info.php .
 *
 * If you are feeling kind and generous, consider supporting the project by
 * making a donation at: http://www.jqplot.com/donate.php .
 *
 * sprintf functions contained in jqplot.sprintf.js by Ash Searle:
 *
 *     version 2007.04.27
 *     author Ash Searle
 *     http://hexmen.com/blog/2007/03/printf-sprintf/
 *     http://hexmen.com/js/sprintf.js
 *     The author (Ash Searle) has placed this code in the public domain:
 *     "This code is unrestricted: you are free to use it however you like."
 * 
 */
(function($) {
    // class: $.jqplot.CanvasOverlay
    $.jqplot.CanvasOverlay = function(opts){
		var options = opts || {};
        // Group: Properties
        // prop: show
        // wether or not to show the marker.
        this.options = {
			show: $.jqplot.config.enablePlugins,
			deferDraw: false
		};
		// prop: objects
		this.objects = [];
		this.objectNames = [];
        this.canvas = null;
		this.markerRenderer = new $.jqplot.MarkerRenderer({style:'line'});
		this.markerRenderer.init();
		if (options.objects) {
			var objs = options.objects,
				obj;
			for (var i=0; i<objs.length; i++) {
				obj = objs[i];
				for (var n in obj) {
					switch (n) {
						case 'line':
							this.addLine(obj[n]);
							break;
						case 'horizontalLine':
							this.addHorizontalLine(obj[n]);
							break;
					}
				}	
			}
		}
		$.extend(true, this.options, options);
	};
	
	// called with scope of a plot object
	$.jqplot.CanvasOverlay.postPlotInit = function (target, data, opts) {
        var options = opts || {};
        // add a canvasOverlay attribute to the plot
        this.plugins.canvasOverlay = new $.jqplot.CanvasOverlay(options.canvasOverlay);		
	};
	
	function Line(options) {
		this.type = 'line';
		this.options = {
			name: null,
			show: true,
			lineWidth: 2,
			lineCap: 'round',
			color: '#666666',
	        // prop: shadow
	        // wether or not to draw a shadow on the line
	        shadow: true,
	        // prop: shadowAngle
	        // Shadow angle in degrees
	        shadowAngle: 45,
	        // prop: shadowOffset
	        // Shadow offset from line in pixels
	        shadowOffset: 1,
	        // prop: shadowDepth
	        // Number of times shadow is stroked, each stroke offset shadowOffset from the last.
	        shadowDepth: 3,
	        // prop: shadowAlpha
	        // Alpha channel transparency of shadow.  0 = transparent.
	        shadowAlpha: '0.07',
			xaxis: 'xaxis',
			yaxis: 'yaxis',
			start: [],
			stop: []
		};
		$.extend(true, this.options, options);
	}
	
	function HorizontalLine(options) {
		this.type = 'horizontalLine';
		this.options = {
			name: null,
			show: true,
			lineWidth: 2,
			lineCap: 'round',
			color: '#666666',
	        // prop: shadow
	        // wether or not to draw a shadow on the line
	        shadow: true,
	        // prop: shadowAngle
	        // Shadow angle in degrees
	        shadowAngle: 45,
	        // prop: shadowOffset
	        // Shadow offset from line in pixels
	        shadowOffset: 1,
	        // prop: shadowDepth
	        // Number of times shadow is stroked, each stroke offset shadowOffset from the last.
	        shadowDepth: 3,
	        // prop: shadowAlpha
	        // Alpha channel transparency of shadow.  0 = transparent.
	        shadowAlpha: '0.07',
			xaxis: 'xaxis',
			yaxis: 'yaxis',
			y: null,
			xmin: null,
			xmax: null,
			xOffset: '6px',	// number or string.  Number interpreted as units, string as pixels.
			xminOffset: null,
			xmaxOffset: null
		};
		$.extend(true, this.options, options);
	}
	
	$.jqplot.CanvasOverlay.prototype.addLine = function(opts) {
		var line = new Line(opts);
		this.objects.push(line);
		this.objectNames.push(line.options.name);
	};
	
	$.jqplot.CanvasOverlay.prototype.addHorizontalLine = function(opts) {
		var line = new HorizontalLine(opts);
		this.objects.push(line);
		this.objectNames.push(line.options.name);
	};
	
	$.jqplot.CanvasOverlay.prototype.removeObject = function(idx) {
		// check if integer, remove by index
		if ($.type(idx) == 'number') {
			this.objects.splice(idx, 1);
			this.objectNames.splice(idx, 1);
		}
		// if string, remove by name
		else {
			var id = $.inArray(idx, this.objectNames);
			if (id != -1) {
				this.objects.splice(id, 1);
				this.objectNames.splice(id, 1);
			}
		}
	};
	
	$.jqplot.CanvasOverlay.prototype.getObject = function(idx) {
		// check if integer, remove by index
		if ($.type(idx) == 'number') {
			return this.objects[idx];
		}
		// if string, remove by name
		else {
			var id = $.inArray(idx, this.objectNames);
			if (id != -1) {
				return this.objects[id];
			}
		}
	};
	
	// Set get as alias for getObject.
	$.jqplot.CanvasOverlay.prototype.get = $.jqplot.CanvasOverlay.prototype.getObject;
	
	$.jqplot.CanvasOverlay.prototype.clear = function(plot) {
		this.canvas._ctx.clearRect(0,0,this.canvas.getWidth(), this.canvas.getHeight());
	};
	
	$.jqplot.CanvasOverlay.prototype.draw = function(plot) {
		var obj, 
			objs = this.objects,
			mr = this.markerRenderer,
			start,
			stop;
		if (this.options.show) {
			this.canvas._ctx.clearRect(0,0,this.canvas.getWidth(), this.canvas.getHeight());
			for (var i=0; i<objs.length; i++) {
				obj = objs[i];
				var opts = $.extend(true, {}, obj.options);
				if (obj.options.show) {
					// style and shadow properties should be set before
					// every draw of marker renderer.
					mr.shadow = obj.options.shadow;
					switch (obj.type) {
						case 'line':
							// style and shadow properties should be set before
							// every draw of marker renderer.
							mr.style = 'line';
							opts.closePath = false;
							start = [plot.axes[obj.options.xaxis].u2p(obj.options.start[0]), plot.axes[obj.options.yaxis].u2p(obj.options.start[1])];
							stop = [plot.axes[obj.options.xaxis].u2p(obj.options.stop[0]), plot.axes[obj.options.yaxis].u2p(obj.options.stop[1])];
							mr.draw(start, stop, this.canvas._ctx, opts);
							break;
						case 'horizontalLine':
							
							// style and shadow properties should be set before
							// every draw of marker renderer.
							if (obj.options.y != null) {
								mr.style = 'line';
								opts.closePath = false;
								var xaxis = plot.axes[obj.options.xaxis],
									xstart,
									xstop,
									y = plot.axes[obj.options.yaxis].u2p(obj.options.y),
									xminoff = obj.options.xminOffset || obj.options.xOffset,
									xmaxoff = obj.options.xmaxOffset || obj.options.xOffset;
								if (obj.options.xmin != null) {
									xstart = xaxis.u2p(obj.options.xmin);
								}
								else if (xminoff != null) {
									if ($.type(xminoff) == "number") {
										xstart = xaxis.u2p(xaxis.min + xminoff);
									}
									else if ($.type(xminoff) == "string") {
										xstart = xaxis.u2p(xaxis.min) + parseFloat(xminoff);
									}
								}
								if (obj.options.xmax != null) {
									xstop = xaxis.u2p(obj.options.xmax);
								}
								else if (xmaxoff != null) {
									if ($.type(xmaxoff) == "number") {
										xstop = xaxis.u2p(xaxis.max - xmaxoff);
									}
									else if ($.type(xmaxoff) == "string") {
										xstop = xaxis.u2p(xaxis.max) - parseFloat(xmaxoff);
									}
								}
								if (xstop != null && xstart != null) {
									mr.draw([xstart, y], [xstop, y], this.canvas._ctx, opts);
								}
							}
							break;
					}
				}
			}
		}
	};
    
    // called within context of plot
    // create a canvas which we can draw on.
    // insert it before the eventCanvas, so eventCanvas will still capture events.
    $.jqplot.CanvasOverlay.postPlotDraw = function() {
        this.plugins.canvasOverlay.canvas = new $.jqplot.GenericCanvas();
        
        this.eventCanvas._elem.before(this.plugins.canvasOverlay.canvas.createElement({top:0, right:0, bottom:0, left:0}, 'jqplot-overlayCanvas-canvas', this._plotDimensions));
        this.plugins.canvasOverlay.canvas.setContext();
		if (!this.plugins.canvasOverlay.deferDraw) {
			this.plugins.canvasOverlay.draw(this);
		}
    };
    
    $.jqplot.postInitHooks.push($.jqplot.CanvasOverlay.postPlotInit);
    $.jqplot.postDrawHooks.push($.jqplot.CanvasOverlay.postPlotDraw);

})(jQuery);