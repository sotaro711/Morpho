"use client";

import Plotly from "plotly.js-dist-min";
import { useEffect, useRef } from "react";
import type { PlotParams } from "react-plotly.js";
import createPlotlyComponent from "react-plotly.js/factory";

const PlotlyPlot = createPlotlyComponent(Plotly);

/**
 * react-plotly.js の useResizeHandler は window の resize しか見ないため、
 * ウィンドウ幅は変わらずレイアウトだけ変わるケース（二画面表示への切替など）で
 * チャートが古い幅のまま残る。ResizeObserver でコンテナ自体を監視して追従させる。
 */
export default function Plot(props: PlotParams) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(() => {
      const gd = el.querySelector<HTMLElement>(".js-plotly-plot");
      // 幅 0（非表示など）で resize を呼ぶと Plotly が例外を投げるため除外する
      if (gd && el.clientWidth > 0) Plotly.Plots.resize(gd);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className="w-full min-w-0">
      <PlotlyPlot {...props} />
    </div>
  );
}
