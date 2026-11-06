import { Composition } from "remotion";
import { NavigatorSlide, type NavProps } from "./NavigatorSlide";

const empty: NavProps = { css: "", stageHtml: "", durationInFrames: 1, layer: null };

export const RemotionRoot = () => (
  <Composition
    id="NavigatorSlide"
    component={NavigatorSlide}
    durationInFrames={1}
    fps={30}
    width={1920}
    height={1080}
    defaultProps={empty}
    calculateMetadata={({ props }) => ({ durationInFrames: props.durationInFrames })}
  />
);
