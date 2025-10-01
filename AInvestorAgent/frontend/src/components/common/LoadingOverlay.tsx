export function LoadingOverlay({
  visible,
  message,
  progress = 0,
  steps = [],
  currentStep = 0
}: {
  visible: boolean;
  message: string;
  progress?: number;
  steps?: string[];
  currentStep?: number;
}) {
  if (!visible) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9999] flex items-center justify-center">
      <div className="bg-[#2d2d44] rounded-lg p-8 max-w-md w-full mx-4 border border-gray-700 shadow-2xl">
        <div className="flex justify-center mb-6">
          <div className="relative w-24 h-24">
            <div className="absolute inset-0 border-4 border-transparent border-t-blue-500 border-r-blue-500 rounded-full animate-spin"
                 style={{ animationDuration: '1.2s' }} />
            <div className="absolute inset-2 border-4 border-transparent border-b-purple-500 border-l-purple-500 rounded-full animate-spin"
                 style={{ animationDuration: '1.5s', animationDirection: 'reverse' }} />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl font-bold text-white">{Math.floor(progress)}%</span>
            </div>
          </div>
        </div>
        <h3 className="text-xl font-semibold text-white text-center mb-4">{message}</h3>
        {steps.length > 0 && (
          <div className="space-y-2 mb-4">
            <div className="text-sm text-gray-400 text-center mb-3">步骤 {currentStep + 1} / {steps.length}</div>
            {steps.map((step, idx) => (
              <div key={idx} className="flex items-center gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  idx < currentStep ? 'bg-green-600 text-white' :
                  idx === currentStep ? 'bg-blue-600 text-white animate-pulse' :
                  'bg-gray-700 text-gray-500'
                }`}>{idx < currentStep ? '✓' : idx + 1}</div>
                <span className={`text-sm transition-colors ${idx <= currentStep ? 'text-white font-medium' : 'text-gray-500'}`}>{step}</span>
              </div>
            ))}
          </div>
        )}
        <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 h-2 rounded-full transition-all duration-300 ease-out" style={{ width: `${progress}%` }} />
        </div>
      </div>
    </div>
  );
}