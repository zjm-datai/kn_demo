// src/polyfills.js
import Lame from 'lamejs/src/js/Lame'
import Presets from 'lamejs/src/js/Presets'
import GainAnalysis from 'lamejs/src/js/GainAnalysis'
import QuantizePVT from 'lamejs/src/js/QuantizePVT'
import Quantize from 'lamejs/src/js/Quantize'
import Reservoir from 'lamejs/src/js/Reservoir'
import Takehiro from 'lamejs/src/js/Takehiro'
import MPEGMode from 'lamejs/src/js/MPEGMode'
import BitStream from 'lamejs/src/js/BitStream'

// 挂到全局
window.Lame         = Lame
window.Presets      = Presets
window.GainAnalysis = GainAnalysis
window.QuantizePVT  = QuantizePVT
window.Quantize     = Quantize
window.Reservoir    = Reservoir
window.Takehiro     = Takehiro
window.MPEGMode     = MPEGMode
window.BitStream    = BitStream
