import React, { createContext, useContext, useState } from 'react';

const AppStateContext = createContext();

export const useAppState = () => useContext(AppStateContext);

export const AppStateProvider = ({ children }) => {
    // Global Upload State
    const [uploadState, setUploadState] = useState({
        file: null,
        preview: null,
        result: null,
        loading: false,
        error: null,
        showHeatmap: false,
    });

    // Global Chat State
    const [chatState, setChatState] = useState({
        isOpen: false,
        messages: [],
        sessionId: null,
    });

    return (
        <AppStateContext.Provider value={{
            uploadState,
            setUploadState,
            chatState,
            setChatState
        }}>
            {children}
        </AppStateContext.Provider>
    );
};
