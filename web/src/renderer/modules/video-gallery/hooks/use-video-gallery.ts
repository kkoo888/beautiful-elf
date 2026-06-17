/** 视频画廊 React Query Hooks */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchVideos, fetchVideoTags, fetchVideoById,
  createVideo, updateVideo, deleteVideo, generateVideo,
} from '../services/video-gallery-api'
import type {
  VideoGalleryFormInput, VideoGalleryUpdateInput, VideoGenerateInput,
} from '../types'

const KEY = ['video-gallery']

export function useVideoGallery() {
  const queryClient = useQueryClient()

  const videosQuery = (params?: { tag?: string; enabled?: number; page?: number; pageSize?: number }) =>
    useQuery({
      queryKey: [...KEY, 'list', params],
      queryFn: () => fetchVideos(params),
    })

  const tagsQuery = () =>
    useQuery({
      queryKey: [...KEY, 'tags'],
      queryFn: () => fetchVideoTags(),
    })

  const videoQuery = (id: number) =>
    useQuery({
      queryKey: [...KEY, 'detail', id],
      queryFn: () => fetchVideoById(id),
      enabled: id > 0,
    })

  const createMut = useMutation({
    mutationFn: (input: VideoGalleryFormInput) => createVideo(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY })
    },
  })

  const updateMut = useMutation({
    mutationFn: ({ id, input }: { id: number; input: VideoGalleryUpdateInput }) => updateVideo(id, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY })
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteVideo(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY })
    },
  })

  const generateMut = useMutation({
    mutationFn: (input: VideoGenerateInput) => generateVideo(input),
  })

  return {
    videosQuery,
    tagsQuery,
    videoQuery,
    createVideo: (input: VideoGalleryFormInput) => createMut.mutateAsync(input),
    updateVideo: (id: number, input: VideoGalleryUpdateInput) => updateMut.mutateAsync({ id, input }),
    deleteVideo: (id: number) => deleteMut.mutateAsync(id),
    generateVideo: (input: VideoGenerateInput) => generateMut.mutateAsync(input),
    isCreating: createMut.isPending,
    isUpdating: updateMut.isPending,
    isDeleting: deleteMut.isPending,
    isGenerating: generateMut.isPending,
  }
}
