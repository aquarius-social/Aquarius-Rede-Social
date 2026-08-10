import { useState, type ReactNode } from 'react';
import { View, Text, Pressable, ScrollView, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { raio, fonte, type Tema } from '../lib/tema';
import { useTemaEstilos } from '../lib/theme';
import { useFollows, type Follow } from '../lib/follows';
import { Icon, Card, SectionHeader, Divider, Monogram, Avatar, PartyChip, BottomNav } from '../components/base';
import { AqHeader } from '../components/header';
import { PARTIDO_COR } from '../lib/mock';
import { TEMAS, PARTIDOS } from '../lib/catalogos';

export default function Interesses() {
  const { cor, st } = useTemaEstilos(criarSt);
  const router = useRouter();
  const { porTipo, seguir, deixarDeSeguir } = useFollows();
  const [addTema, setAddTema] = useState(false);
  const [addPartido, setAddPartido] = useState(false);

  const parlamentares = porTipo('parlamentar');
  const partidos = porTipo('partido');
  const frentes = porTipo('frente');
  const temas = porTipo('tema');

  const temSigla = new Set(partidos.map((p) => p.ref_id));
  const temTema = new Set(temas.map((t) => t.ref_id));
  const partidosRestantes = PARTIDOS.filter((p) => !temSigla.has(p));
  const temasRestantes = TEMAS.filter((t) => !temTema.has(t));

  const total = parlamentares.length + partidos.length + frentes.length + temas.length;

  return (
    <View style={{ flex: 1, backgroundColor: cor.surface }}>
      <AqHeader variant="home" />
      <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 12, paddingBottom: 100 }}>
        <Text style={st.h1}>Interesses</Text>
        <Text style={st.sub}>
          {total
            ? `Você acompanha ${total} ${total === 1 ? 'item' : 'itens'}. Tudo isso guia o seu feed.`
            : 'Siga parlamentares, partidos, frentes e temas — eles passam a guiar o seu feed.'}
        </Text>

        {/* ── Parlamentares ── */}
        <View style={{ height: 18 }} />
        <SectionHeader title="Seus parlamentares" />
        {parlamentares.length ? (
          <Card padding={0}>
            {parlamentares.map((f, i) => (
              <View key={f.ref_id}>
                <LinhaFollow
                  st={st} cor={cor}
                  leading={<Avatar nome={f.rotulo ?? '?'} size={40} />}
                  nome={f.rotulo ?? 'Parlamentar'}
                  chip={<PartyChip sigla={metaStr(f, 'sigla')} uf={metaStr(f, 'uf')} />}
                  onOpen={() => router.push({ pathname: '/parlamentar/[id]', params: { id: f.ref_id } })}
                  onRemove={() => deixarDeSeguir('parlamentar', f.ref_id)}
                />
                {i < parlamentares.length - 1 ? <Divider inset={66} /> : null}
              </View>
            ))}
          </Card>
        ) : (
          <EmptyMini texto="Você ainda não segue ninguém. Abra o perfil de um parlamentar e toque em Seguir." />
        )}

        {/* ── Partidos e frentes ── */}
        <View style={{ height: 20 }} />
        <SectionHeader title="Seus partidos e frentes" action={
          <Pressable onPress={() => setAddPartido((v) => !v)}><Text style={st.acao}>{addPartido ? 'Fechar' : 'Adicionar'}</Text></Pressable>
        } />
        {addPartido ? (
          <View style={st.picker}>
            {partidosRestantes.length ? partidosRestantes.map((p) => (
              <Pressable key={p} onPress={() => seguir({ tipo: 'partido', ref_id: p, rotulo: p })} style={st.pickerChip}>
                <Icon name="plus" size={12} color={cor.sky} /><Text style={st.pickerChipTxt}>{p}</Text>
              </Pressable>
            )) : <Text style={st.vazioMini}>Você já segue todos os partidos da lista.</Text>}
          </View>
        ) : null}
        {partidos.length || frentes.length ? (
          <Card padding={0}>
            {partidos.map((f, i) => (
              <View key={'pt' + f.ref_id}>
                <LinhaFollow
                  st={st} cor={cor}
                  leading={<Monogram sigla={f.ref_id} size={40} color={PARTIDO_COR[f.ref_id] ?? cor.navy} />}
                  nome={f.ref_id}
                  onOpen={() => router.push({ pathname: '/partido/[sigla]', params: { sigla: f.ref_id } })}
                  onRemove={() => deixarDeSeguir('partido', f.ref_id)}
                />
                {(i < partidos.length - 1 || frentes.length) ? <Divider inset={66} /> : null}
              </View>
            ))}
            {frentes.map((f, i) => (
              <View key={'fr' + f.ref_id}>
                <LinhaFollow
                  st={st} cor={cor}
                  leading={<View style={st.frenteIcon}><Icon name="star" size={18} color={cor.white} /></View>}
                  nome={f.rotulo ?? 'Frente'}
                  onOpen={() => router.push({ pathname: '/frente/[id]', params: { id: f.ref_id } })}
                  onRemove={() => deixarDeSeguir('frente', f.ref_id)}
                />
                {i < frentes.length - 1 ? <Divider inset={66} /> : null}
              </View>
            ))}
          </Card>
        ) : <EmptyMini texto="Nenhum partido ou frente ainda. Toque em Adicionar (partidos) ou siga uma frente no perfil dela." />}

        {/* ── Temas ── */}
        <View style={{ height: 20 }} />
        <SectionHeader title="Seus temas" action={
          <Pressable onPress={() => setAddTema((v) => !v)}><Text style={st.acao}>{addTema ? 'Fechar' : 'Adicionar'}</Text></Pressable>
        } />
        {addTema ? (
          <View style={st.picker}>
            {temasRestantes.length ? temasRestantes.map((t) => (
              <Pressable key={t} onPress={() => seguir({ tipo: 'tema', ref_id: t, rotulo: t })} style={st.pickerChip}>
                <Icon name="plus" size={12} color={cor.sky} /><Text style={st.pickerChipTxt}>{t}</Text>
              </Pressable>
            )) : <Text style={st.vazioMini}>Você já segue todos os temas.</Text>}
          </View>
        ) : null}
        {temas.length ? (
          <View style={st.chipsWrap}>
            {temas.map((t) => (
              <Pressable key={t.ref_id} onPress={() => deixarDeSeguir('tema', t.ref_id)} style={st.chip}>
                <Text style={st.chipTxt}># {t.ref_id}</Text><Icon name="x" size={11} color={cor.mutedSoft} />
              </Pressable>
            ))}
          </View>
        ) : <EmptyMini texto="Nenhum tema ainda. Toque em Adicionar." />}
      </ScrollView>

      <BottomNav active="interesses" />
    </View>
  );
}

/** Extrai um campo string de follow.meta (jsonb) com segurança. */
function metaStr(f: Follow, chave: string): string | null {
  const v = f.meta?.[chave];
  return typeof v === 'string' ? v : null;
}

function LinhaFollow({ st, cor, leading, nome, chip, onOpen, onRemove }: {
  st: ReturnType<typeof criarSt>; cor: Tema;
  leading: ReactNode; nome: string; chip?: ReactNode;
  onOpen: () => void; onRemove: () => void;
}) {
  return (
    <View style={st.linha}>
      <Pressable style={st.linhaMain} onPress={onOpen}>
        {leading}
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={st.linhaNome} numberOfLines={1}>{nome}</Text>
          {chip ? <View style={{ flexDirection: 'row' }}>{chip}</View> : null}
        </View>
        <Icon name="chevR" size={16} color={cor.mutedSoft} />
      </Pressable>
      <Pressable onPress={onRemove} hitSlop={8} style={st.remover}>
        <Icon name="x" size={15} color={cor.mutedSoft} />
      </Pressable>
    </View>
  );
}

function EmptyMini({ texto }: { texto: string }) {
  const { st } = useTemaEstilos(criarSt);
  return <Text style={st.vazio}>{texto}</Text>;
}

const criarSt = (cor: Tema) => StyleSheet.create({
  h1: { fontSize: 26, fontFamily: fonte.xb, color: cor.texto, letterSpacing: -0.5, marginTop: 4 },
  sub: { marginTop: 2, fontSize: 12.5, fontFamily: fonte.r, color: cor.muted, lineHeight: 18 },
  acao: { fontFamily: fonte.b, fontSize: 12, color: cor.sky },
  chipsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  chip: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 9999, backgroundColor: cor.light },
  chipTxt: { fontFamily: fonte.sb, fontSize: 12.5, color: cor.texto },
  picker: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12, padding: 12, borderRadius: raio.card, borderWidth: 1, borderColor: cor.border, backgroundColor: cor.cartao },
  pickerChip: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 11, paddingVertical: 7, borderRadius: 9999, backgroundColor: cor.cartao, borderWidth: 1, borderStyle: 'dashed', borderColor: cor.borderStrong },
  pickerChipTxt: { fontFamily: fonte.b, fontSize: 12, color: cor.sky },
  linha: { flexDirection: 'row', alignItems: 'center' },
  linhaMain: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 11, paddingLeft: 12 },
  linhaNome: { fontFamily: fonte.b, fontSize: 14, color: cor.texto },
  frenteIcon: { width: 40, height: 40, borderRadius: 9999, backgroundColor: cor.skySoft, alignItems: 'center', justifyContent: 'center' },
  remover: { paddingHorizontal: 14, paddingVertical: 12 },
  vazio: { marginTop: 4, fontFamily: fonte.r, fontSize: 12.5, color: cor.mutedSoft, lineHeight: 18 },
  vazioMini: { fontFamily: fonte.r, fontSize: 12, color: cor.mutedSoft },
});
