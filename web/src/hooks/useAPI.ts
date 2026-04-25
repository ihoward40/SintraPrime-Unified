import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { APIError } from '../api/client';

// Generic fetch hook
export function useAPIQuery<T>(
  key: string | (string | number | undefined)[],
  fetcher: () => Promise<{ data: T }>,
  options?: {
    enabled?: boolean;
    refetchInterval?: number;
    staleTime?: number;
    onError?: (error: APIError) => void;
  }
) {
  return useQuery({
    queryKey: Array.isArray(key) ? key : [key],
    queryFn: async () => {
      const response = await fetcher();
      return response.data;
    },
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval,
    staleTime: options?.staleTime ?? 5 * 60 * 1000, // 5 min default
  });
}

// Generic mutation hook
export function useAPIMutation<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<{ data: TData }>,
  options?: {
    onSuccess?: (data: TData) => void;
    onError?: (error: APIError) => void;
    invalidateKeys?: string[][];
  }
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (variables: TVariables) => {
      const response = await mutationFn(variables);
      return response.data;
    },
    onSuccess: (data) => {
      options?.onSuccess?.(data);
      // Invalidate specified query keys
      options?.invalidateKeys?.forEach((key) => {
        queryClient.invalidateQueries({ queryKey: key });
      });
    },
    onError: (error) => {
      options?.onError?.(error as APIError);
    },
  });
}
