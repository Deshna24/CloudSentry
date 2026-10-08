import { useCallback, useEffect, useRef, useState } from 'react';

/** Calls `fn` now and every `interval` ms. Never overlaps requests; keeps the last good data on error. */
export function usePolling(fn, interval = 5000, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const busy = useRef(false);

  const run = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      const data = await fnRef.current();
      setState({ data, error: null, loading: false });
    } catch (error) {
      setState((s) => ({ ...s, error, loading: false }));
    } finally {
      busy.current = false;
    }
  }, []);

  useEffect(() => {
    setState((s) => ({ ...s, loading: s.data === null }));
    run();
    if (!interval) return undefined;
    const id = setInterval(() => !document.hidden && run(), interval);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interval, run, ...deps]);

  return { ...state, refresh: run };
}
