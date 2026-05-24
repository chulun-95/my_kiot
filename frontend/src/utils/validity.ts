import type { FormEvent } from 'react';

type ValidityMessages = {
  valueMissing?: string;
  tooShort?: string;
  tooLong?: string;
  typeMismatch?: string;
  patternMismatch?: string;
  rangeUnderflow?: string;
  rangeOverflow?: string;
  default?: string;
};

type InputLike = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;

export function viValidity(messages: ValidityMessages) {
  return {
    onInvalid: (e: FormEvent<InputLike>) => {
      const el = e.currentTarget;
      const v = el.validity;
      let msg = messages.default ?? 'Giá trị không hợp lệ';
      if (v.valueMissing && messages.valueMissing) msg = messages.valueMissing;
      else if (v.tooShort && messages.tooShort) msg = messages.tooShort;
      else if (v.tooLong && messages.tooLong) msg = messages.tooLong;
      else if (v.typeMismatch && messages.typeMismatch) msg = messages.typeMismatch;
      else if (v.patternMismatch && messages.patternMismatch) msg = messages.patternMismatch;
      else if (v.rangeUnderflow && messages.rangeUnderflow) msg = messages.rangeUnderflow;
      else if (v.rangeOverflow && messages.rangeOverflow) msg = messages.rangeOverflow;
      el.setCustomValidity(msg);
    },
    onInput: (e: FormEvent<InputLike>) => {
      e.currentTarget.setCustomValidity('');
    },
  };
}
