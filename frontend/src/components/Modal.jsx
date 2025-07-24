import { h } from 'preact';

const Modal = ({ isOpen, onClose, title, children, actions }) => {
  if (!isOpen) {
    return null;
  }

  return (
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
      <div class="relative mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
        <div class="mt-3 text-center">
          <div class="flex justify-between items-center pb-3">
            <h3 class="text-lg leading-6 font-medium text-gray-900">{title}</h3>
            <button 
              onClick={onClose} 
              class="text-gray-400 bg-transparent hover:bg-gray-200 hover:text-gray-900 rounded-lg text-sm p-1.5 ml-auto inline-flex items-center"
              aria-label="Close modal"
            >
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>
            </button>
          </div>
          <div class="mt-2 px-7 py-3">
            <div class="text-sm text-gray-500">
              {children}
            </div>
          </div>
          {actions && (
            <div class="items-center px-4 py-3">
              {actions}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Modal; 