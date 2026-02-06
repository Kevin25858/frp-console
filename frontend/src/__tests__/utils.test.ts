/**
 * 前端工具函数测试
 */

import { describe, it, expect } from 'vitest';
import { cn } from '../lib/utils';

describe('Utils', () => {
  describe('cn function', () => {
    it('should merge class names correctly', () => {
      expect(cn('btn', 'btn-primary')).toBe('btn btn-primary');
    });

    it('should handle conditional classes', () => {
      expect(cn('btn', false && 'hidden', 'active')).toBe('btn active');
    });

    it('should merge tailwind classes correctly', () => {
      expect(cn('px-2', 'py-1')).toBe('px-2 py-1');
    });

    it('should handle undefined and null', () => {
      expect(cn(undefined, null, 'btn')).toBe('btn');
    });
  });
});