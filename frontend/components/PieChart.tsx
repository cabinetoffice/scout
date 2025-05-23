import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

interface PieChartProps {
  data: number[];
  labels: string[];
  onClickURL: string;
}

const PieChart: React.FC<PieChartProps> = ({ data, labels, onClickURL }) => {
  const ref = useRef<SVGSVGElement | null>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ref.current || !containerRef.current) return;

    // Get container dimensions for responsive sizing
    const containerWidth = containerRef.current.clientWidth;
    const containerHeight = containerRef.current.clientHeight;
    
    const width = Math.min(containerWidth, 400);
    const height = Math.min(containerHeight, 300);
    const radius = Math.min(width, height) / 3;

    // Clear previous chart
    d3.select(ref.current).selectAll("*").remove();

    // Define a color scale
    const color = d3
      .scaleOrdinal<string>()
      .domain(labels)
      .range([
        "#4e79a7",
        "#f28e2c",
        "#e15759",
        "#76b7b2",
        "#59a14f",
        "#edc949",
        "#af7aa1",
        "#ff9da7",
        "#9c755f",
        "#bab0ab",
      ]);

    const pie = d3.pie<number>().value((d) => d)(data);
    const arc = d3
      .arc<d3.PieArcDatum<number>>()
      .innerRadius(0)
      .outerRadius(radius);

    const svg = d3
      .select(ref.current)
      .attr("width", width)
      .attr("height", height);

    const chartGroup = svg
      .append("g")
      .attr("transform", `translate(${width / 3}, ${height / 2})`);

    const tooltip = d3
      .select(tooltipRef.current)
      .style("position", "absolute")
      .style("background-color", "white")
      .style("padding", "10px")
      .style("border", "1px solid #ccc")
      .style("border-radius", "5px")
      .style("box-shadow", "0 0 10px rgba(0, 0, 0, 0.1)")
      .style("pointer-events", "none")
      .style("opacity", 0);

    const onMouseOver = (event: MouseEvent, d: d3.PieArcDatum<number>) => {
      tooltip.transition().duration(200).style("opacity", 1);
      tooltip
        .html(`${labels[d.index]}: ${d.value}`)
        .style("left", `${event.pageX + 10}px`)
        .style("top", `${event.pageY + 10}px`);
    };

    const onMouseMove = (event: MouseEvent) => {
      tooltip
        .style("left", `${event.pageX + 10}px`)
        .style("top", `${event.pageY + 10}px`);
    };

    const onMouseOut = () => {
      tooltip.transition().duration(200).style("opacity", 0);
    };

    const onClick = (d: d3.PieArcDatum<number>) => {
      const label = labels[d.index];
      const url = `${onClickURL}?answer=${encodeURIComponent(label)}`;
      window.location.href = url;
    };

    chartGroup
      .selectAll("path")
      .data(pie)
      .enter()
      .append("path")
      .attr("d", arc)
      .attr("fill", (d, i) => color(i.toString()) as string)
      .on("mouseover", function (event, d) {
        d3.select(this).transition().duration(200).attr("opacity", 0.7);
        d3.select(this).attr("cursor", "pointer");
        onMouseOver(event as unknown as MouseEvent, d);
      })
      .on("mousemove", function (event, d) {
        onMouseMove(event as unknown as MouseEvent);
      })
      .on("mouseout", function (event, d) {
        d3.select(this).transition().duration(200).attr("opacity", 1);
        onMouseOut();
      })
      .on("click", function (event, d) {
        d3.select(this).transition().duration(200).attr("opacity", 1);
        onClick(d);
      });

    // Add responsive legend
    const legend = svg
      .append("g")
      .attr("transform", `translate(${width / 3 + radius + 20}, ${height / 2 - (labels.length * 15) / 2})`);

    labels.forEach((label, i) => {
      const legendRow = legend
        .append("g")
        .attr("transform", `translate(0, ${i * 15})`);

      legendRow
        .append("rect")
        .attr("width", 8)
        .attr("height", 8)
        .attr("fill", color(i.toString()) as string);

      legendRow
        .append("text")
        .attr("x", 12)
        .attr("y", 8)
        .attr("text-anchor", "start")
        .style("font-size", "12px")
        .style("text-transform", "capitalize")
        .text(label);
    });

    return () => {
      d3.select(ref.current).selectAll("*").remove();
    };
  }, [data, labels, onClickURL]);

  return (
    <div
      ref={containerRef}
      style={{ 
        width: "100%", 
        height: "100%", 
        display: "flex", 
        alignItems: "center", 
        justifyContent: "center",
        minHeight: "200px"
      }}
    >
      <svg ref={ref}></svg>
      <div ref={tooltipRef} className="tooltip"></div>
    </div>
  );
};

export default PieChart;