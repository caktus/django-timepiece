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
(function(b){b.jqplot.CanvasOverlay=function(f){var d=f||{};this.options={show:b.jqplot.config.enablePlugins,deferDraw:false};this.objects=[];this.objectNames=[];this.canvas=null;this.markerRenderer=new b.jqplot.MarkerRenderer({style:"line"});this.markerRenderer.init();if(d.objects){var h=d.objects,g;for(var e=0;e<h.length;e++){g=h[e];for(var j in g){switch(j){case"line":this.addLine(g[j]);break;case"horizontalLine":this.addHorizontalLine(g[j]);break}}}}b.extend(true,this.options,d)};b.jqplot.CanvasOverlay.postPlotInit=function(g,f,e){var d=e||{};this.plugins.canvasOverlay=new b.jqplot.CanvasOverlay(d.canvasOverlay)};function c(d){this.type="line";this.options={name:null,show:true,lineWidth:2,lineCap:"round",color:"#666666",shadow:true,shadowAngle:45,shadowOffset:1,shadowDepth:3,shadowAlpha:"0.07",xaxis:"xaxis",yaxis:"yaxis",start:[],stop:[]};b.extend(true,this.options,d)}function a(d){this.type="horizontalLine";this.options={name:null,show:true,lineWidth:2,lineCap:"round",color:"#666666",shadow:true,shadowAngle:45,shadowOffset:1,shadowDepth:3,shadowAlpha:"0.07",xaxis:"xaxis",yaxis:"yaxis",y:null,xmin:null,xmax:null,xOffset:"6px",xminOffset:null,xmaxOffset:null};b.extend(true,this.options,d)}b.jqplot.CanvasOverlay.prototype.addLine=function(e){var d=new c(e);this.objects.push(d);this.objectNames.push(d.options.name)};b.jqplot.CanvasOverlay.prototype.addHorizontalLine=function(e){var d=new a(e);this.objects.push(d);this.objectNames.push(d.options.name)};b.jqplot.CanvasOverlay.prototype.removeObject=function(d){if(b.type(d)=="number"){this.objects.splice(d,1);this.objectNames.splice(d,1)}else{var e=b.inArray(d,this.objectNames);if(e!=-1){this.objects.splice(e,1);this.objectNames.splice(e,1)}}};b.jqplot.CanvasOverlay.prototype.getObject=function(d){if(b.type(d)=="number"){return this.objects[d]}else{var e=b.inArray(d,this.objectNames);if(e!=-1){return this.objects[e]}}};b.jqplot.CanvasOverlay.prototype.get=b.jqplot.CanvasOverlay.prototype.getObject;b.jqplot.CanvasOverlay.prototype.clear=function(d){this.canvas._ctx.clearRect(0,0,this.canvas.getWidth(),this.canvas.getHeight())};b.jqplot.CanvasOverlay.prototype.draw=function(n){var k,m=this.objects,h=this.markerRenderer,g,p;if(this.options.show){this.canvas._ctx.clearRect(0,0,this.canvas.getWidth(),this.canvas.getHeight());for(var l=0;l<m.length;l++){k=m[l];var e=b.extend(true,{},k.options);if(k.options.show){h.shadow=k.options.shadow;switch(k.type){case"line":h.style="line";e.closePath=false;g=[n.axes[k.options.xaxis].u2p(k.options.start[0]),n.axes[k.options.yaxis].u2p(k.options.start[1])];p=[n.axes[k.options.xaxis].u2p(k.options.stop[0]),n.axes[k.options.yaxis].u2p(k.options.stop[1])];h.draw(g,p,this.canvas._ctx,e);break;case"horizontalLine":if(k.options.y!=null){h.style="line";e.closePath=false;var q=n.axes[k.options.xaxis],r,j,o=n.axes[k.options.yaxis].u2p(k.options.y),d=k.options.xminOffset||k.options.xOffset,f=k.options.xmaxOffset||k.options.xOffset;if(k.options.xmin!=null){r=q.u2p(k.options.xmin)}else{if(d!=null){if(b.type(d)=="number"){r=q.u2p(q.min+d)}else{if(b.type(d)=="string"){r=q.u2p(q.min)+parseFloat(d)}}}}if(k.options.xmax!=null){j=q.u2p(k.options.xmax)}else{if(f!=null){if(b.type(f)=="number"){j=q.u2p(q.max-f)}else{if(b.type(f)=="string"){j=q.u2p(q.max)-parseFloat(f)}}}}if(j!=null&&r!=null){h.draw([r,o],[j,o],this.canvas._ctx,e)}}break}}}}};b.jqplot.CanvasOverlay.postPlotDraw=function(){this.plugins.canvasOverlay.canvas=new b.jqplot.GenericCanvas();this.eventCanvas._elem.before(this.plugins.canvasOverlay.canvas.createElement({top:0,right:0,bottom:0,left:0},"jqplot-overlayCanvas-canvas",this._plotDimensions));this.plugins.canvasOverlay.canvas.setContext();if(!this.plugins.canvasOverlay.deferDraw){this.plugins.canvasOverlay.draw(this)}};b.jqplot.postInitHooks.push(b.jqplot.CanvasOverlay.postPlotInit);b.jqplot.postDrawHooks.push(b.jqplot.CanvasOverlay.postPlotDraw)})(jQuery);