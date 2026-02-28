# SPL File I/O Specification — Summary

## Overview

Added **Section 13bis: Fichiers — Port‑Mapped I/O** to SPL-spec-fr.md

This specification enables SPL programs to read and write files sequentially, enabling persistent data storage for:
- Educational applications (flashcard apps with score tracking)
- Games with progress saving
- Data editors and management tools
- Configuration files

## Port Mapping

| Port | Name        | R/W | Purpose                    |
|------|-------------|-----|----------------------------|
| 0xA0 | FILE_CMD    | W   | Commands: 0=noop, 1=open, 2=close |
| 0xA1 | FILE_MODE   | W   | Mode: 0=read, 1=write, 2=append |
| 0xA2 | FILE_DATA   | R/W | Read/write single byte     |
| 0xA3 | FILE_STATUS | R   | Status: bit0=EOF, bit1=ERROR, bit7=OPEN |
| 0xA4 | FILE_NAME   | W   | Filename (write char-by-char, null-terminated) |

## Key Features

✅ **Sequential Access Only**
- No seek/random access (simplified model)
- Read and write files sequentially, byte by byte

✅ **Single File Open**
- Only one file can be open at a time
- Opening a new file auto-closes the previous one

✅ **Simple Error Handling**
- EOF flag (bit0 of FILE_STATUS)
- ERROR flag (bit1) for file not found, permissions, disk full, etc.

✅ **ASCII Filenames Only**
- Filenames < 256 characters
- Characters must be ASCII 0x20-0x7E (printable)
- Null-terminated (0x00)

## Three Modes

### READ (0)
- Open existing file for reading
- Returns 0 at EOF
- FILE_STATUS.EOF = 1 when end reached

### WRITE (1)
- Create new file or truncate existing
- Overwrites file contents
- Creates file if it doesn't exist

### APPEND (2)
- Open file for appending
- Writes go to end of file
- Creates file if it doesn't exist

## Usage Pattern

### Opening a File

```lisp
; Write filename byte-by-byte, null-terminated
(push 0x64) (out 0xA4)  ; 'd'
(push 0x61) (out 0xA4)  ; 'a'
(push 0x74) (out 0xA4)  ; 't'
(push 0x61) (out 0xA4)  ; 'a'
(push 0x00) (out 0xA4)  ; null

; Set mode (read=0, write=1, append=2)
(push 0) (out 0xA1)

; Open
(push 1) (out 0xA0)

; Check for errors
(in 0xA3)
(push 2) (and)          ; bit1 = ERROR
(jump-if-not-zero handle-error)
```

### Reading Sequentially

```lisp
(label read-loop)
(in 0xA3)               ; Get status
(push 1) (and)          ; bit0 = EOF?
(jump-if-not-zero done)

(in 0xA2)               ; Read byte
; ... process byte ...

(jump read-loop)

(label done)
(push 2) (out 0xA0)     ; Close
```

### Writing Sequentially

```lisp
(push 0x48) (out 0xA2)  ; 'H'
(push 0x65) (out 0xA2)  ; 'e'
(push 0x6C) (out 0xA2)  ; 'l'
(push 0x6C) (out 0xA2)  ; 'l'
(push 0x6F) (out 0xA2)  ; 'o'

(in 0xA3)
(push 2) (and)          ; Check error
(jump-if-not-zero write-error)

(push 2) (out 0xA0)     ; Close
```

## Changes to Spec Document

### Table of Contents
- Added: 13bis. #13bis-fichiers--portmapped-io

### Section 17 (Capabilities Discovery)
- Added File I/O as optional extension
- Programs can attempt to use and detect support via error flag

### Section 18.6 (New Profile: SPL-Persistent-App)
- Documents profile for applications with persistent data
- Includes recommended memory layout
- Shows initialization pattern for loading data on startup

## Implementation Requirements

### Core Profile (Required)

✅ Sequential read and write
✅ File open/close
✅ Basic error detection (file not found, disk full)
✅ Filename support up to 255 chars

### Extended Profile (Optional)

🔹 APPEND mode
🔹 Directory support
🔹 Relative path support
🔹 Sandboxed filesystem access (security)

## Security Considerations

For VM implementations running in restricted environments:

1. **Sandbox paths** — Restrict files to a safe directory
2. **Block absolute paths** — Reject filenames starting with `/`
3. **Block directory traversal** — Reject `../` sequences
4. **Optional extension filtering** — Only allow safe file types

## Examples in Spec

Section 13bis includes:

1. **Basic Read Pattern** — Open, read until EOF, close
2. **Basic Write Pattern** — Open, write bytes, close
3. **Error Handling** — Check FILE_STATUS.ERROR
4. **Complete Example** — Full read-and-display program

Section 18.6 includes:

1. **Persistent App Init** — Load data on startup
2. **Data Format Example** — Simple text format with sections
3. **Save on Exit** — Write progress back to file

## Compatibility

✅ **Fully Portable** — Part of SPL spec, not VM-specific
✅ **Backward Compatible** — Optional; old code without file I/O still works
✅ **Forward Compatible** — Simple design allows future extensions
✅ **Implementation Flexible** — Each VM implements as appropriate (OS file system vs embedded storage)

## Next Steps

1. ✅ Specification written and documented
2. ⏭️ Implement in Python VM (spl_vm.py)
3. ⏭️ Create flashcard-editor.spl (backoffice in SPL)
4. ⏭️ Create flashcard-player.spl (updated app in SPL)
5. ⏭️ Test with data.txt format

## Document Locations

- **Full Specification**: `SPL-spec-fr.md` § 13bis
- **Capability Discovery**: `SPL-spec-fr.md` § 17
- **Application Profile**: `SPL-spec-fr.md` § 18.6
- **Implementation Guide**: `SPL-spec-fr.md` § 20 (Notes)

---

**Status**: ✅ Specification Complete and Documented
**Date**: 2026-02-24
**Version**: SPL Spec v1.0 + File I/O Extension
