export { VisualPanel } from './visual-panel'
export { CapturePreview } from './components/capture-preview'
export { AnalysisPanel } from './components/analysis-panel'
export { FrameSettings } from './components/frame-settings'
export { useCapture } from './hooks/use-capture'
export { useFrameDetector } from './hooks/use-frame-detector'
export { captureScreen, analyzeImage } from './services/visual-api'
export type {
  CaptureMode,
  AnalysisMode,
  CaptureResult,
  AnalysisResult,
  FrameChangeConfig,
} from './types/visual'
