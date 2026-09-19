-- Gerador procedural do sprite do Mossnib (Aseprite / Lua).
--
-- Esta é a FONTE da arte: o .aseprite e o .png exportados são derivados.
-- Para alterar o personagem, edite aqui e rode de novo, assim todas as
-- 16 poses saem consistentes entre si (é isso que evita o efeito "cada
-- frame parece outro bicho" que acontece com geração por IA).
--
-- Técnica: o corpo é uma esfera com iluminação Lambert calculada por
-- pixel, quantizada numa rampa de 8 tons (paleta musgo/outono: pouco
-- saturada, brilho quente/dourado em vez de verde-limão vivo), mais
-- especular, luz de borda (rim light), textura de musgo por ruído e
-- contorno seletivo. A silhueta usa uma função de "barriga" (mais larga
-- perto de ny=0.28, afinando de novo perto do fundo) em vez de ser uma
-- bola perfeita.
--
-- As 4 perninhas são formas arredondadas desenhadas de verdade (círculos
-- com raio x/y próprio), coloridas com tons da MESMA rampa do corpo
-- (traseiras menores/mais escuras, dianteiras maiores/mais claras,
-- seguindo a mesma direção de luz do corpo) — pedido do dev: pernas
-- devem se confundir com o corpo, não ser blobs de cor destacada.
-- (Tentativa anterior usava perturbação de raio na silhueta pra criar as
-- pernas, mas isso gerava bicos pontudos em vez de nubs macios.)
--
-- Sem blush nas bochechas — removido a pedido do dev (o rosa não ficou
-- bom / muito acentuado).
--
-- Uso (via MCP aseprite script_execute), com params:
--   params.sheet = caminho do PNG da spritesheet (16 frames na horizontal)
--   params.ase   = caminho do .aseprite com os 16 frames
--
-- Frames: 0-3 idle (respiração) | 4-6 andar direita | 7-9 andar esquerda
--         10-12 carinho (clique) | 13-15 soltando folha

local W,H = 64,64
local NF = 16
local sheetPath = params.sheet
local asePath = params.ase

local function rgba(r,g,b,a) return app.pixelColor.rgba(r,g,b,a or 255) end

local ramp = {
  {0x21,0x2C,0x1A},{0x30,0x40,0x27},{0x43,0x54,0x35},{0x57,0x66,0x40},
  {0x6E,0x79,0x4C},{0x88,0x8B,0x57},{0xA9,0xA1,0x69},{0xD3,0xC5,0x8C},
}
local leafRamp = {
  {0x20,0x30,0x17},{0x33,0x4B,0x1F},{0x49,0x66,0x29},
  {0x60,0x77,0x35},{0x7E,0x86,0x44},{0xA3,0x9F,0x5D},
}
local function noise(x,y)
  local v=math.sin(x*12.9898+y*78.233)*43758.5453
  return v-math.floor(v)
end
local Lx,Ly,Lz=-0.50,-0.62,0.60
local ll=math.sqrt(Lx*Lx+Ly*Ly+Lz*Lz); Lx,Ly,Lz=Lx/ll,Ly/ll,Lz/ll

-- so tufos de musgo na silhueta (as pernas sao desenhadas a parte, abaixo)
local tufts = {
  {-2.75,0.055,0.24},{-2.25,0.040,0.20},{-1.75,0.060,0.22},
  {-0.55,0.055,0.22},{ 0.15,0.035,0.18},{ 2.95,0.045,0.20},
}

local function render(o)
  local img = Image(W,H,ColorMode.RGB)
  local sx, sy   = o.sx or 1.0, o.sy or 1.0
  local lean     = o.lean or 0.0
  local bob      = o.bob or 0.0
  local sway     = o.sway or 0.0

  local function setPx(x,y,c)
    x=math.floor(x); y=math.floor(y)
    if x<0 or y<0 or x>=W or y>=H then return end
    img:drawPixel(x,y,c)
  end
  local function setRamp(x,y,i)
    if i<1 then i=1 elseif i>8 then i=8 end
    local c=ramp[i]; setPx(x,y,rgba(c[1],c[2],c[3],255))
  end
  local function getA(x,y)
    x=math.floor(x); y=math.floor(y)
    if x<0 or y<0 or x>=W or y>=H then return 0 end
    return app.pixelColor.rgbaA(img:getPixel(x,y))
  end
  local function blend(x,y,r,g,b,t)
    x=math.floor(x); y=math.floor(y)
    if getA(x,y)==0 then return end
    local c=img:getPixel(x,y)
    local ar,ag,ab=app.pixelColor.rgbaR(c),app.pixelColor.rgbaG(c),app.pixelColor.rgbaB(c)
    img:drawPixel(x,y,rgba(math.floor(ar+(r-ar)*t),math.floor(ag+(g-ag)*t),math.floor(ab+(b-ab)*t),255))
  end

  local BCX, BCY, BRX, BRY = 32.0, 36.0, 21.0, 22.0
  local rxE, ryE = BRX*sx, BRY*sy
  local cyE = BCY + BRY - ryE + bob
  local cxE = BCX

  local function bellyWiden(ny)
    local bulge = 0.24*math.exp(-((ny-0.28)*(ny-0.28))/(2*0.16*0.16))
    local taper = 0.16*math.max(0, ny-0.72)
    return 1.0 + 0.05*ny + bulge - taper
  end

  local function norm(x,y)
    local ny=(y+0.5-cyE)/ryE
    local shear = lean*(-ny)*ryE*0.16
    local nx=(x+0.5-cxE-shear)/(rxE*bellyWiden(ny))
    return nx, ny
  end
  local function edgeR(nx,ny)
    local ang=math.atan(ny,nx); local r=1.0
    for _,t in ipairs(tufts) do
      local d=ang-t[1]
      while d> math.pi do d=d-2*math.pi end
      while d<-math.pi do d=d+2*math.pi end
      r=r+t[2]*math.exp(-(d*d)/(2*t[3]*t[3]))
    end
    return r
  end
  local function inBody(x,y)
    local nx,ny=norm(x,y)
    return math.sqrt(nx*nx+ny*ny)<=edgeR(nx,ny)
  end
  local function T(dx,dy)
    local ny=dy/BRY
    local shear=lean*(-ny)*ryE*0.16
    return cxE+dx*sx+shear, cyE+dy*sy
  end

  -- corpo
  for y=0,H-1 do
    for x=0,W-1 do
      if inBody(x,y) then
        local nx,ny=norm(x,y)
        local d2=nx*nx+ny*ny; if d2>1 then d2=1 end
        local nz=math.sqrt(1-d2)
        local lam=nx*Lx+ny*Ly+nz*Lz; if lam<0 then lam=0 end
        local v=0.15+0.97*lam
        local e=(d2-0.52)/0.48
        if e>0 then
          local rd=nx*0.60+ny*0.80
          if rd>0.05 then v=v+e*e*(rd-0.05)*1.15 end
        end
        local i=3+math.floor(v*4.9)
        local sdx=(nx+0.38)/0.32
        local sdy=(ny+0.48)/0.21
        if sdx*sdx+sdy*sdy<1.0 then i=8
        elseif sdx*sdx+sdy*sdy<2.1 and i<7 then i=7 end
        local nv=noise(math.floor(x/3),math.floor(y/3))
        if nv>0.84 then i=i-1 elseif nv<0.13 and lam>0.5 then i=i+1 end
        setRamp(x,y,i)
      end
    end
  end

  local edges={}
  for y=0,H-1 do
    for x=0,W-1 do
      if inBody(x,y) and ((not inBody(x-1,y)) or (not inBody(x+1,y))
         or (not inBody(x,y-1)) or (not inBody(x,y+1))) then
        local nx,ny=norm(x,y)
        local f=nx*Lx+ny*Ly
        edges[#edges+1]={x,y,(f<-0.55) and 3 or ((f<-0.15) and 2 or 1)}
      end
    end
  end
  for _,o2 in ipairs(edges) do setRamp(o2[1],o2[2],o2[3]) end

  for _,f in ipairs({{-19,-7},{-16,-15},{-9,-20},{11,-18},{18,-11},{20,-1},{14,14},{-13,12}}) do
    local px,py=T(f[1],f[2])
    if getA(px,py)==0 then setRamp(px,py,2) end
  end

  -- 4 perninhas redondas, tons da mesma rampa do corpo
  local function leg(dx,dy,rx,ry,fillIdx,outlineIdx)
    local px,py=T(dx,dy)
    for y=math.floor(py-ry-1),math.floor(py+ry+1) do
      for x=math.floor(px-rx-1),math.floor(px+rx+1) do
        local ex=(x+0.5-px)/rx
        local ey=(y+0.5-py)/ry
        local d=ex*ex+ey*ey
        if d<=1.0 then
          if d>0.62 then setRamp(x,y,outlineIdx) else setRamp(x,y,fillIdx) end
        end
      end
    end
  end
  leg(-6, 15.5, 2.5, 2.1, 3, 1)   -- traseira esquerda (sombra)
  leg( 6, 15.5, 2.5, 2.1, 4, 1)   -- traseira direita
  leg(-11,18.5, 3.3, 2.7, 5, 2)   -- dianteira esquerda (mais luz)
  leg( 11,18.5, 3.3, 2.7, 4, 1)   -- dianteira direita

  -- caule
  local function bez(p0,p1,p2,t) local m=1-t; return m*m*p0+2*m*t*p1+t*t*p2 end
  for i=0,48 do
    local t=i/48
    local dx=bez(0.0,-2.5,1.5+sway,t)
    local dy=bez(-17.0,-22.0,-27.0,t)
    local px,py=T(dx,dy)
    local c3,c2,c4=leafRamp[3],leafRamp[2],leafRamp[4]
    setPx(px,py,rgba(c3[1],c3[2],c3[3]))
    setPx(px+1,py,rgba(c2[1],c2[2],c2[3]))
    setPx(px-1,py,rgba(c4[1],c4[2],c4[3]))
  end
  for dx=-3,3 do
    for dy=-18,-15 do
      local px,py=T(dx,dy)
      if getA(px,py)>0 then blend(px,py,0x22,0x2E,0x18,0.32) end
    end
  end

  local function drawLeaf(bdx,bdy,tdx,tdy,width,flip)
    local bx,by=T(bdx,bdy)
    local tx,ty=T(tdx,tdy)
    local ddx,ddy=tx-bx,ty-by
    local len=math.sqrt(ddx*ddx+ddy*ddy)
    local ux,uy=ddx/len,ddy/len
    local vx,vy=-uy,ux
    for y=math.floor(math.min(by,ty)-width-2),math.ceil(math.max(by,ty)+width+2) do
      for x=math.floor(math.min(bx,tx)-width-2),math.ceil(math.max(bx,tx)+width+2) do
        local ex,ey=x+0.5-bx,y+0.5-by
        local t=ex*ux+ey*uy
        local s=ex*vx+ey*vy
        if t>=0 and t<=len then
          local tt=t/len
          local hw=width*math.sin(math.pi*(tt^0.70))
          if hw>0.40 and math.abs(s)<=hw then
            local i
            if math.abs(s)/hw>0.80 then i=1
            else
              i=3
              if s*flip<-hw*0.15 then i=4 end
              if s*flip<-hw*0.55 then i=5 end
              if s*flip> hw*0.45 then i=2 end
              if math.abs(s)<0.85 and tt>0.12 and tt<0.90 then i=2 end
              if tt<0.42 and s*flip<-hw*0.34 then i=math.min(6,i+1) end
            end
            local c=leafRamp[i]; setPx(x,y,rgba(c[1],c[2],c[3]))
          end
        end
      end
    end
  end
  drawLeaf(1.0,-26.0, 16.0+sway*2.0,-33.5, 4.6, 1.0)
  drawLeaf(-0.5,-23.5,-13.0+sway*1.4,-30.5, 3.6,-1.0)

  local eyeMode = o.eye or "open"
  local function eyeOpen(ddx)
    local ex,ey=T(ddx,-2)
    for y=math.floor(ey)-7,math.floor(ey)+7 do
      for x=math.floor(ex)-6,math.floor(ex)+6 do
        local dx=(x+0.5-ex)/(4.3*sx)
        local dy=(y+0.5-ey)/(5.4*sy)
        local d=dx*dx+dy*dy
        if d<=1 then
          if d>0.62 and (y-ey)>2 then setPx(x,y,rgba(0x1E,0x28,0x16))
          else setPx(x,y,rgba(0x0F,0x14,0x0A)) end
        end
      end
    end
    setPx(ex-2,ey-4,rgba(255,255,255)); setPx(ex-1,ey-4,rgba(255,255,255))
    setPx(ex-3,ey-3,rgba(255,255,255)); setPx(ex-2,ey-3,rgba(255,255,255))
    setPx(ex-1,ey-3,rgba(240,246,230)); setPx(ex-2,ey-2,rgba(226,236,214))
    setPx(ex+2,ey+2,rgba(145,150,120)); setPx(ex+2,ey+3,rgba(115,120,95))
  end
  local function eyeHappy(ddx)
    local ex,ey=T(ddx,-2)
    local c=rgba(0x0F,0x14,0x0A)
    for k=-4,4 do
      local yy = ey + math.abs(k)*0.55 - 1
      setPx(ex+k, yy, c); setPx(ex+k, yy+1, c)
    end
  end
  local function eyeBlink(ddx)
    local ex,ey=T(ddx,-2)
    local c=rgba(0x0F,0x14,0x0A)
    for k=-4,4 do setPx(ex+k,ey+1,c); setPx(ex+k,ey+2,c) end
  end
  for _,ddx in ipairs({-10,10}) do
    if eyeMode=="happy" then eyeHappy(ddx)
    elseif eyeMode=="blink" then eyeBlink(ddx)
    else eyeOpen(ddx) end
  end

  local mc=rgba(0x1A,0x22,0x12)
  if (o.mouth or "smile")=="big" then
    for _,p in ipairs({{-6,4},{-5,5},{-4,6},{-3,7},{-2,8},{-1,8},{0,8},{1,8},{2,8},{3,7},{4,6},{5,5},{6,4}}) do
      local px,py=T(p[1],p[2]); setPx(px,py,mc)
    end
    for _,p in ipairs({{-3,8},{-2,9},{-1,9},{0,9},{1,9},{2,9},{3,8}}) do
      local px,py=T(p[1],p[2]); setPx(px,py,mc)
    end
  else
    for _,p in ipairs({{-5,5},{-4,6},{-3,7},{-2,8},{-1,8},{0,8},{1,8},{2,7},{3,6},{4,5}}) do
      local px,py=T(p[1],p[2]); setPx(px,py,mc)
    end
    for _,p in ipairs({{-2,9},{-1,9},{0,9},{1,9}}) do
      local px,py=T(p[1],p[2]); setPx(px,py,mc)
    end
  end

  if o.hearts then
    local hc=rgba(0xE0,0x8F,0x7E)
    local hc2=rgba(0xF0,0xC0,0xA8)
    for _,h in ipairs(o.hearts) do
      for _,p in ipairs({{0,0},{1,0},{3,0},{4,0},{0,1},{1,1},{2,1},{3,1},{4,1},{1,2},{2,2},{3,2},{2,3}}) do
        setPx(h[1]+p[1],h[2]+p[2],hc)
      end
      setPx(h[1]+1,h[2]+1,hc2)
    end
  end

  if o.fallLeaf then
    local fx,fy,rot = o.fallLeaf[1], o.fallLeaf[2], o.fallLeaf[3]
    local ux,uy = math.cos(rot), math.sin(rot)
    local vx,vy = -uy, ux
    for y=fy-5,fy+5 do
      for x=fx-6,fx+6 do
        local ex,ey=x+0.5-fx,y+0.5-fy
        local t=ex*ux+ey*uy
        local s=ex*vx+ey*vy
        if math.abs(t)<=5 then
          local hw=2.3*math.sin(math.pi*((t+5)/10))
          if hw>0.35 and math.abs(s)<=hw then
            local i = (math.abs(s)/hw>0.75) and 1 or ((s<0) and 5 or 3)
            local c=leafRamp[i]; setPx(x,y,rgba(c[1],c[2],c[3]))
          end
        end
      end
    end
  end

  return img
end

local frames = {}
frames[1] = render{sx=1.000, sy=1.000, sway=0.0,  bob=0}
frames[2] = render{sx=1.015, sy=1.022, sway=0.4,  bob=-0.5}
frames[3] = render{sx=1.028, sy=1.042, sway=0.8,  bob=-1}
frames[4] = render{sx=1.015, sy=1.022, sway=0.4,  bob=-0.5}
frames[5] = render{sx=1.02, sy=0.975, lean= 0.55, bob=0,    sway=-0.5}
frames[6] = render{sx=0.98, sy=1.030, lean= 0.85, bob=-2,   sway=-1.1}
frames[7] = render{sx=1.01, sy=0.990, lean= 0.65, bob=-0.5, sway=-0.7}
frames[8] = render{sx=1.02, sy=0.975, lean=-0.55, bob=0,    sway=0.5}
frames[9] = render{sx=0.98, sy=1.030, lean=-0.85, bob=-2,   sway=1.1}
frames[10]= render{sx=1.01, sy=0.990, lean=-0.65, bob=-0.5, sway=0.7}
frames[11]= render{sx=1.10, sy=0.88, eye="blink", mouth="smile", bob=0, sway=-0.6}
frames[12]= render{sx=0.94, sy=1.12, eye="happy", mouth="big", bob=-3, sway=1.2,
                   hearts={{46,8},{12,14}}}
frames[13]= render{sx=1.02, sy=0.99, eye="happy", mouth="big", bob=-1, sway=0.4,
                   hearts={{48,4}}}
frames[14]= render{sx=1.05, sy=0.95, sway=-1.4, bob=0}
frames[15]= render{sx=0.97, sy=1.05, sway=1.6, bob=-1, fallLeaf={50,20,0.6}}
frames[16]= render{sx=1.00, sy=1.00, sway=0.6, bob=0, fallLeaf={54,32,1.4}}

local sheet = Image(W*NF, H, ColorMode.RGB)
for i=1,NF do sheet:drawImage(frames[i], Point((i-1)*W, 0)) end
local sspr = Sprite(W*NF, H)
if #sspr.cels>0 then sspr.cels[1].image=sheet
else sspr:newCel(sspr.layers[1],1,sheet,Point(0,0)) end
sspr:saveAs(sheetPath)
sspr:close()

local aspr = Sprite(W,H)
for i=2,NF do aspr:newEmptyFrame(i) end
local lay = aspr.layers[1]
for i=1,NF do
  local existing = nil
  for _,c in ipairs(aspr.cels) do if c.frameNumber==i then existing=c end end
  if existing then existing.image = frames[i]
  else aspr:newCel(lay, i, frames[i], Point(0,0)) end
end
aspr:saveAs(asePath)
aspr:close()
print("frames="..NF)
