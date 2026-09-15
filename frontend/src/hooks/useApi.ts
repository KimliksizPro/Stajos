import { useState, useCallback } from 'react';

export function useApi<T, P extends any[]>(fetchFn: (...args: P) => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(
    async (...args: P) => {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchFn(...args);
        setData(result);
        return result;
      } catch (err: any) {
        setError(err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [fetchFn]
  );

  return { data, loading, error, execute, refetch: execute };
}
