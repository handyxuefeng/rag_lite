  

const value = [
     100,
     97,
     116,
     97,
     58,
     32,
     123,
     34,
     116,
     121,
     112,
     101,
     34,
     58,
     32,
     34,
     99,
     111,
     110,
     116,
     101,
     110,
     116,
     34,
     44,
     32,
     34,
     99,
     111,
     110,
     116,
     101,
     110,
     116,
     34,
     58,
     32,
     34,
     227,
     128,
     130,
     34,
     125,
     10,
     10
]
// Uint8Array(20) [100, 97, 116, 97, 58, 32, 123, 34, 116, 121, 112, 101, 34, 58, 34, 99, 111, 110, 116, 101, 110, 116, 34, 125, 10, 10]
// 对应的文本是: "data: {"type":"content"}\n\n"
const decoder = new TextDecoder();
const uint8Array = new Uint8Array(value);
console.log(uint8Array);
const text = decoder.decode(uint8Array);
console.log(text);