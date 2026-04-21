from . import models, controllers


def _seed_knowledge_hub(env):
    import logging, importlib.util, os
    _log = logging.getLogger(__name__)
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        seed_path = os.path.join(here, 'data', 'seed_vocab.py')
        spec = importlib.util.spec_from_file_location('seed_vocab', seed_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        count = env['language.seeded.word']._seed_from_json(mod.VOCAB_DATA)
        if count:
            _log.info('language_portal: seeded %d new words', count)
    except Exception:
        _log.exception('language_portal: word seeding failed')
    try:
        _seed_grammar(env)
    except Exception:
        _log.exception('language_portal: grammar seeding failed')


def _seed_grammar(env):
    GS = env['language.grammar.section'].sudo()
    # Skip only if all 6 sections already have full content (not stubs)
    if GS.search_count([('content_html', 'not like', 'stub')]) >= 6:
        return

    sections = [
        {
            'title': 'All 12 English Tenses',
            'slug': 'tenses',
            'category': 'tenses',
            'sequence': 10,
            'content_html': '''
<h2>The 12 English Tenses</h2>
<p>English has 12 main tenses formed by combining 3 time frames (past, present, future) with 4 aspects (simple, continuous, perfect, perfect continuous).</p>

<h3>1. Present Simple</h3>
<p><strong>Form:</strong> Subject + base verb (he/she/it adds <em>-s</em>)</p>
<p><strong>Use:</strong> Habits, facts, schedules.</p>
<p><em>I work every day. She speaks English well.</em></p>
<p><strong>Ukrainian:</strong> Теперішній простий час</p>

<h3>2. Present Continuous</h3>
<p><strong>Form:</strong> Subject + am/is/are + verb-ing</p>
<p><strong>Use:</strong> Actions happening now; temporary situations.</p>
<p><em>I am working right now. They are studying.</em></p>
<p><strong>Ukrainian:</strong> Теперішній тривалий час</p>

<h3>3. Present Perfect</h3>
<p><strong>Form:</strong> Subject + have/has + past participle</p>
<p><strong>Use:</strong> Past actions with present relevance; experience.</p>
<p><em>I have visited Paris. She has just arrived.</em></p>
<p><strong>Ukrainian:</strong> Теперішній перфектний час</p>

<h3>4. Present Perfect Continuous</h3>
<p><strong>Form:</strong> Subject + have/has been + verb-ing</p>
<p><strong>Use:</strong> Actions that started in the past and continue now.</p>
<p><em>I have been working here for 5 years.</em></p>

<h3>5. Past Simple</h3>
<p><strong>Form:</strong> Subject + past tense (regular: -ed; irregular: see table)</p>
<p><strong>Use:</strong> Completed actions at a specific past time.</p>
<p><em>She worked yesterday. I saw him last week.</em></p>
<p><strong>Ukrainian:</strong> Минулий простий час</p>

<h3>6. Past Continuous</h3>
<p><strong>Form:</strong> Subject + was/were + verb-ing</p>
<p><strong>Use:</strong> Actions in progress at a specific past moment.</p>
<p><em>I was sleeping when you called.</em></p>

<h3>7. Past Perfect</h3>
<p><strong>Form:</strong> Subject + had + past participle</p>
<p><strong>Use:</strong> Action completed before another past action.</p>
<p><em>She had already left when I arrived.</em></p>

<h3>8. Past Perfect Continuous</h3>
<p><strong>Form:</strong> Subject + had been + verb-ing</p>
<p><strong>Use:</strong> Action ongoing up to a point in the past.</p>
<p><em>He had been waiting for two hours before the bus came.</em></p>

<h3>9. Future Simple (will)</h3>
<p><strong>Form:</strong> Subject + will + base verb</p>
<p><strong>Use:</strong> Predictions, spontaneous decisions, promises.</p>
<p><em>I will call you tomorrow. It will rain.</em></p>
<p><strong>Ukrainian:</strong> Майбутній простий час</p>

<h3>10. Future Continuous</h3>
<p><strong>Form:</strong> Subject + will be + verb-ing</p>
<p><strong>Use:</strong> Actions in progress at a specific future moment.</p>
<p><em>This time tomorrow I will be flying to London.</em></p>

<h3>11. Future Perfect</h3>
<p><strong>Form:</strong> Subject + will have + past participle</p>
<p><strong>Use:</strong> Action completed before a specific future point.</p>
<p><em>By Friday I will have finished the report.</em></p>

<h3>12. Future Perfect Continuous</h3>
<p><strong>Form:</strong> Subject + will have been + verb-ing</p>
<p><strong>Use:</strong> Duration of an action up to a future point.</p>
<p><em>By June she will have been studying English for 10 years.</em></p>

<hr/>
<h3>Quick Reference Timeline</h3>
<table class="table table-bordered table-sm">
<thead><tr><th>Aspect</th><th>Past</th><th>Present</th><th>Future</th></tr></thead>
<tbody>
<tr><td>Simple</td><td>worked</td><td>work/works</td><td>will work</td></tr>
<tr><td>Continuous</td><td>was working</td><td>am/is/are working</td><td>will be working</td></tr>
<tr><td>Perfect</td><td>had worked</td><td>have/has worked</td><td>will have worked</td></tr>
<tr><td>Perf. Cont.</td><td>had been working</td><td>have/has been working</td><td>will have been working</td></tr>
</tbody>
</table>
''',
        },
        {
            'title': 'Irregular Verbs',
            'slug': 'irregular-verbs',
            'category': 'verbs',
            'sequence': 20,
            'content_html': '''
<h2>Common Irregular Verbs</h2>
<p>Irregular verbs do not follow the standard <em>-ed</em> pattern. Memorise these common forms.</p>
<table class="table table-bordered table-sm table-hover">
<thead class="table-dark"><tr><th>Base</th><th>Past Simple</th><th>Past Participle</th><th>Ukrainian</th></tr></thead>
<tbody>
<tr><td>be</td><td>was/were</td><td>been</td><td>бути</td></tr>
<tr><td>beat</td><td>beat</td><td>beaten</td><td>бити</td></tr>
<tr><td>become</td><td>became</td><td>become</td><td>ставати</td></tr>
<tr><td>begin</td><td>began</td><td>begun</td><td>починати</td></tr>
<tr><td>break</td><td>broke</td><td>broken</td><td>ламати</td></tr>
<tr><td>bring</td><td>brought</td><td>brought</td><td>приносити</td></tr>
<tr><td>build</td><td>built</td><td>built</td><td>будувати</td></tr>
<tr><td>buy</td><td>bought</td><td>bought</td><td>купувати</td></tr>
<tr><td>catch</td><td>caught</td><td>caught</td><td>ловити</td></tr>
<tr><td>choose</td><td>chose</td><td>chosen</td><td>вибирати</td></tr>
<tr><td>come</td><td>came</td><td>come</td><td>приходити</td></tr>
<tr><td>cut</td><td>cut</td><td>cut</td><td>різати</td></tr>
<tr><td>do</td><td>did</td><td>done</td><td>робити</td></tr>
<tr><td>draw</td><td>drew</td><td>drawn</td><td>малювати</td></tr>
<tr><td>drink</td><td>drank</td><td>drunk</td><td>пити</td></tr>
<tr><td>drive</td><td>drove</td><td>driven</td><td>водити</td></tr>
<tr><td>eat</td><td>ate</td><td>eaten</td><td>їсти</td></tr>
<tr><td>fall</td><td>fell</td><td>fallen</td><td>падати</td></tr>
<tr><td>feel</td><td>felt</td><td>felt</td><td>відчувати</td></tr>
<tr><td>find</td><td>found</td><td>found</td><td>знаходити</td></tr>
<tr><td>fly</td><td>flew</td><td>flown</td><td>літати</td></tr>
<tr><td>forget</td><td>forgot</td><td>forgotten</td><td>забувати</td></tr>
<tr><td>get</td><td>got</td><td>got/gotten</td><td>отримувати</td></tr>
<tr><td>give</td><td>gave</td><td>given</td><td>давати</td></tr>
<tr><td>go</td><td>went</td><td>gone</td><td>іти</td></tr>
<tr><td>grow</td><td>grew</td><td>grown</td><td>рости</td></tr>
<tr><td>have</td><td>had</td><td>had</td><td>мати</td></tr>
<tr><td>hear</td><td>heard</td><td>heard</td><td>чути</td></tr>
<tr><td>hide</td><td>hid</td><td>hidden</td><td>ховати</td></tr>
<tr><td>hit</td><td>hit</td><td>hit</td><td>вдаряти</td></tr>
<tr><td>hold</td><td>held</td><td>held</td><td>тримати</td></tr>
<tr><td>keep</td><td>kept</td><td>kept</td><td>тримати/зберігати</td></tr>
<tr><td>know</td><td>knew</td><td>known</td><td>знати</td></tr>
<tr><td>lead</td><td>led</td><td>led</td><td>вести</td></tr>
<tr><td>leave</td><td>left</td><td>left</td><td>залишати</td></tr>
<tr><td>lend</td><td>lent</td><td>lent</td><td>позичати</td></tr>
<tr><td>let</td><td>let</td><td>let</td><td>дозволяти</td></tr>
<tr><td>lose</td><td>lost</td><td>lost</td><td>губити/програвати</td></tr>
<tr><td>make</td><td>made</td><td>made</td><td>робити</td></tr>
<tr><td>mean</td><td>meant</td><td>meant</td><td>означати</td></tr>
<tr><td>meet</td><td>met</td><td>met</td><td>зустрічати</td></tr>
<tr><td>pay</td><td>paid</td><td>paid</td><td>платити</td></tr>
<tr><td>put</td><td>put</td><td>put</td><td>класти</td></tr>
<tr><td>read</td><td>read</td><td>read</td><td>читати</td></tr>
<tr><td>ride</td><td>rode</td><td>ridden</td><td>їхати верхи</td></tr>
<tr><td>ring</td><td>rang</td><td>rung</td><td>дзвонити</td></tr>
<tr><td>rise</td><td>rose</td><td>risen</td><td>підніматися</td></tr>
<tr><td>run</td><td>ran</td><td>run</td><td>бігти</td></tr>
<tr><td>say</td><td>said</td><td>said</td><td>говорити</td></tr>
<tr><td>see</td><td>saw</td><td>seen</td><td>бачити</td></tr>
<tr><td>sell</td><td>sold</td><td>sold</td><td>продавати</td></tr>
<tr><td>send</td><td>sent</td><td>sent</td><td>відправляти</td></tr>
<tr><td>set</td><td>set</td><td>set</td><td>встановлювати</td></tr>
<tr><td>show</td><td>showed</td><td>shown</td><td>показувати</td></tr>
<tr><td>shut</td><td>shut</td><td>shut</td><td>закривати</td></tr>
<tr><td>sing</td><td>sang</td><td>sung</td><td>співати</td></tr>
<tr><td>sit</td><td>sat</td><td>sat</td><td>сидіти</td></tr>
<tr><td>sleep</td><td>slept</td><td>slept</td><td>спати</td></tr>
<tr><td>speak</td><td>spoke</td><td>spoken</td><td>говорити</td></tr>
<tr><td>spend</td><td>spent</td><td>spent</td><td>витрачати</td></tr>
<tr><td>stand</td><td>stood</td><td>stood</td><td>стояти</td></tr>
<tr><td>steal</td><td>stole</td><td>stolen</td><td>красти</td></tr>
<tr><td>swim</td><td>swam</td><td>swum</td><td>плавати</td></tr>
<tr><td>take</td><td>took</td><td>taken</td><td>брати</td></tr>
<tr><td>teach</td><td>taught</td><td>taught</td><td>вчити</td></tr>
<tr><td>tell</td><td>told</td><td>told</td><td>розповідати</td></tr>
<tr><td>think</td><td>thought</td><td>thought</td><td>думати</td></tr>
<tr><td>throw</td><td>threw</td><td>thrown</td><td>кидати</td></tr>
<tr><td>understand</td><td>understood</td><td>understood</td><td>розуміти</td></tr>
<tr><td>wake</td><td>woke</td><td>woken</td><td>прокидатися</td></tr>
<tr><td>wear</td><td>wore</td><td>worn</td><td>носити</td></tr>
<tr><td>win</td><td>won</td><td>won</td><td>вигравати</td></tr>
<tr><td>write</td><td>wrote</td><td>written</td><td>писати</td></tr>
</tbody>
</table>
<p class="text-muted small mt-2">Tip: Group them by pattern — verbs like bring/bring/brought, buy/bought/bought, catch/caught/caught all share the <em>-ought</em> ending.</p>
''',
        },
        {
            'title': 'Articles: a, an, the, zero',
            'slug': 'articles',
            'category': 'articles',
            'sequence': 30,
            'content_html': '''
<h2>English Articles</h2>
<p>English has three article types: <strong>indefinite</strong> (a/an), <strong>definite</strong> (the), and <strong>zero article</strong> (no article).</p>

<h3>A / An — Indefinite Article</h3>
<p>Use with singular countable nouns when referring to <em>any one</em> of a group or introducing something new.</p>
<ul>
<li><strong>a</strong> — before consonant sounds: <em>a book, a university (yoo-sound), a European</em></li>
<li><strong>an</strong> — before vowel sounds: <em>an apple, an hour (silent h), an MBA</em></li>
</ul>
<p><em>I saw a dog. She is an engineer.</em></p>
<p><strong>Ukrainian:</strong> Немає прямого відповідника; передається контекстом.</p>

<h3>The — Definite Article</h3>
<p>Use when the listener already knows which specific thing you mean.</p>
<table class="table table-sm table-bordered">
<thead><tr><th>When to use <em>the</em></th><th>Example</th></tr></thead>
<tbody>
<tr><td>Already mentioned</td><td><em>I saw a dog. The dog was huge.</em></td></tr>
<tr><td>Unique objects</td><td><em>the sun, the moon, the Earth</em></td></tr>
<tr><td>Superlatives</td><td><em>the best, the tallest building</em></td></tr>
<tr><td>Ordinal numbers (first use)</td><td><em>the first time</em></td></tr>
<tr><td>Rivers, mountain ranges, seas</td><td><em>the Nile, the Alps, the Pacific</em></td></tr>
<tr><td>Countries with plural/republic names</td><td><em>the UK, the USA, the Netherlands</em></td></tr>
</tbody>
</table>
<p><strong>Ukrainian:</strong> Відповідає вказівним займенникам (цей, той) або контексту.</p>

<h3>Zero Article (∅)</h3>
<p>No article used with:</p>
<ul>
<li>Plural and uncountable nouns in general statements: <em>Dogs are friendly. Water is essential.</em></li>
<li>Proper names (most): <em>Paris, Ukraine, John</em></li>
<li>Languages: <em>She speaks English.</em></li>
<li>Meals, sports, academic subjects: <em>We had dinner. He plays football. She studies physics.</em></li>
<li>Transport phrases: <em>by car, by train</em></li>
</ul>

<h3>Common Mistakes</h3>
<table class="table table-sm table-bordered table-striped">
<thead><tr><th>Wrong</th><th>Correct</th><th>Rule</th></tr></thead>
<tbody>
<tr><td>I go to the school.</td><td>I go to school.</td><td>Institutions in general purpose</td></tr>
<tr><td>She plays the tennis.</td><td>She plays tennis.</td><td>Sports → zero article</td></tr>
<tr><td>Life is the beautiful.</td><td>Life is beautiful.</td><td>General abstract noun</td></tr>
<tr><td>I like the music.</td><td>I like music.</td><td>Uncountable in general</td></tr>
</tbody>
</table>

<h3>Greek Equivalents</h3>
<p>Greek has a definite article (ο/η/το) that agrees in gender and number. It is used more frequently than English <em>the</em>.</p>
<p><em>the dog → ο σκύλος (masc.) / η γάτα (fem.) cat</em></p>
''',
        },
        {
            'title': 'Conditionals 0–3',
            'slug': 'conditionals',
            'category': 'conditionals',
            'sequence': 40,
            'content_html': '''
<h2>English Conditionals</h2>
<p>Conditionals express "if" situations. There are four main types.</p>

<h3>Zero Conditional — General Truths</h3>
<p><strong>Form:</strong> If + present simple, present simple</p>
<p><strong>Use:</strong> Facts, scientific truths, things that are always true.</p>
<p><em>If you heat water to 100°C, it boils.</em></p>
<p><em>If I miss the bus, I walk.</em></p>
<p><strong>Ukrainian:</strong> Якщо нагріти воду до 100°C, вона закипає.</p>
<p><strong>Greek:</strong> Αν ζεστάνεις νερό στους 100°C, βράζει.</p>

<h3>First Conditional — Real Future Possibility</h3>
<p><strong>Form:</strong> If + present simple, will + base verb</p>
<p><strong>Use:</strong> Realistic conditions and their likely results.</p>
<p><em>If it rains, I will stay at home.</em></p>
<p><em>If you study hard, you will pass the exam.</em></p>
<p><strong>Ukrainian:</strong> Якщо піде дощ, я залишуся вдома.</p>

<h3>Second Conditional — Unreal Present/Future</h3>
<p><strong>Form:</strong> If + past simple, would + base verb</p>
<p><strong>Use:</strong> Hypothetical or unlikely situations; giving advice.</p>
<p><em>If I had a million dollars, I would travel the world.</em></p>
<p><em>If I were you, I would apologize.</em></p>
<p class="text-info small">⚠️ Use <em>were</em> (not <em>was</em>) with all persons in formal English: <em>If she were here…</em></p>
<p><strong>Ukrainian:</strong> Якби в мене був мільйон доларів, я б подорожував світом.</p>

<h3>Third Conditional — Unreal Past</h3>
<p><strong>Form:</strong> If + past perfect, would have + past participle</p>
<p><strong>Use:</strong> Imagining a different outcome to a past event; regrets.</p>
<p><em>If I had studied harder, I would have passed the exam.</em></p>
<p><em>If she had left earlier, she wouldn't have missed the train.</em></p>
<p><strong>Ukrainian:</strong> Якби я більше вчився, я б склав іспит.</p>

<hr/>
<h3>Mixed Conditionals</h3>
<p>You can mix 2nd and 3rd conditionals to show a past cause with a present effect, or vice versa.</p>
<p><em>If I had taken the job (past), I would be richer now (present).</em></p>
<p><em>If I were more organised (present), I would have finished this yesterday (past).</em></p>

<h3>Quick Summary Table</h3>
<table class="table table-bordered table-sm">
<thead class="table-dark"><tr><th>Type</th><th>If-clause</th><th>Main clause</th><th>Use</th></tr></thead>
<tbody>
<tr><td>Zero</td><td>present simple</td><td>present simple</td><td>General truth</td></tr>
<tr><td>First</td><td>present simple</td><td>will + base</td><td>Real possibility</td></tr>
<tr><td>Second</td><td>past simple</td><td>would + base</td><td>Unreal/hypothetical</td></tr>
<tr><td>Third</td><td>past perfect</td><td>would have + pp</td><td>Unreal past</td></tr>
</tbody>
</table>
''',
        },
        {
            'title': 'Modal Verbs',
            'slug': 'modal-verbs',
            'category': 'modals',
            'sequence': 50,
            'content_html': '''
<h2>Modal Verbs</h2>
<p>Modal verbs express ability, permission, obligation, possibility, and advice. They are followed by a <strong>bare infinitive</strong> (no <em>to</em>).</p>

<h3>Can / Could</h3>
<table class="table table-sm table-bordered">
<thead><tr><th>Modal</th><th>Meaning</th><th>Example</th><th>Ukrainian</th></tr></thead>
<tbody>
<tr><td>can</td><td>ability (present)</td><td>I can swim.</td><td>вміти / могти</td></tr>
<tr><td>can</td><td>permission (informal)</td><td>Can I open the window?</td><td>можна?</td></tr>
<tr><td>could</td><td>ability (past)</td><td>She could run fast as a child.</td><td>міг/могла (past)</td></tr>
<tr><td>could</td><td>polite request</td><td>Could you help me?</td><td>чи не могли б ви?</td></tr>
<tr><td>could</td><td>possibility</td><td>It could be true.</td><td>може бути</td></tr>
</tbody>
</table>

<h3>May / Might</h3>
<table class="table table-sm table-bordered">
<tbody>
<tr><td>may</td><td>formal permission</td><td>You may leave now.</td><td>можете (офіційно)</td></tr>
<tr><td>may</td><td>possibility (~50%)</td><td>It may rain later.</td><td>можливо</td></tr>
<tr><td>might</td><td>weaker possibility (~30%)</td><td>It might rain.</td><td>може бути (менша впевненість)</td></tr>
</tbody>
</table>

<h3>Must / Have to</h3>
<table class="table table-sm table-bordered">
<tbody>
<tr><td>must</td><td>strong obligation (internal)</td><td>I must finish this today.</td><td>мусити / повинен</td></tr>
<tr><td>must</td><td>deduction (certainty)</td><td>She must be tired.</td><td>напевно</td></tr>
<tr><td>have to</td><td>obligation (external)</td><td>I have to wear a uniform.</td><td>треба / необхідно</td></tr>
<tr><td>must not</td><td>prohibition</td><td>You must not smoke here.</td><td>не можна / заборонено</td></tr>
<tr><td>don't have to</td><td>no obligation</td><td>You don't have to come.</td><td>не обов'язково</td></tr>
</tbody>
</table>

<h3>Should / Ought to</h3>
<table class="table table-sm table-bordered">
<tbody>
<tr><td>should</td><td>advice/recommendation</td><td>You should see a doctor.</td><td>слід / варто</td></tr>
<tr><td>should</td><td>expectation</td><td>The bus should arrive soon.</td><td>має (мав би)</td></tr>
<tr><td>ought to</td><td>moral obligation/advice</td><td>You ought to apologize.</td><td>варто / мати б</td></tr>
</tbody>
</table>

<h3>Would</h3>
<table class="table table-sm table-bordered">
<tbody>
<tr><td>would</td><td>conditional</td><td>I would help if I could.</td><td>б (умовний спосіб)</td></tr>
<tr><td>would</td><td>polite request</td><td>Would you like some tea?</td><td>чи не хотіли б ви?</td></tr>
<tr><td>would</td><td>past habit</td><td>We would visit her every summer.</td><td>бувало / раніше завжди</td></tr>
</tbody>
</table>

<h3>Modal Verbs in Greek</h3>
<ul>
<li><em>can</em> → μπορώ (boró)</li>
<li><em>must</em> → πρέπει (prépi)</li>
<li><em>should</em> → πρέπει / θα έπρεπε</li>
<li><em>may/might</em> → μπορεί (borei) / ίσως (ísōs)</li>
</ul>
''',
        },
        {
            'title': 'Passive Voice & Reported Speech',
            'slug': 'passive-reported',
            'category': 'voice',
            'sequence': 60,
            'content_html': '''
<h2>Passive Voice</h2>
<p>The passive voice focuses on the <strong>action</strong> or <strong>object</strong> rather than the agent (doer).</p>

<h3>Passive Formation</h3>
<p><strong>Form:</strong> Subject + be (conjugated) + past participle [+ by + agent]</p>
<table class="table table-bordered table-sm">
<thead class="table-dark"><tr><th>Tense</th><th>Active</th><th>Passive</th></tr></thead>
<tbody>
<tr><td>Present Simple</td><td>They make cars here.</td><td>Cars are made here.</td></tr>
<tr><td>Past Simple</td><td>Someone stole my bike.</td><td>My bike was stolen.</td></tr>
<tr><td>Future Simple</td><td>They will announce the results.</td><td>The results will be announced.</td></tr>
<tr><td>Present Perfect</td><td>They have built a new road.</td><td>A new road has been built.</td></tr>
<tr><td>Present Continuous</td><td>They are fixing the roof.</td><td>The roof is being fixed.</td></tr>
</tbody>
</table>

<h3>When to Use Passive</h3>
<ul>
<li>Agent is unknown: <em>The window was broken.</em></li>
<li>Agent is unimportant: <em>The report was submitted on time.</em></li>
<li>Formal/scientific writing: <em>The experiment was conducted…</em></li>
<li>To avoid blame: <em>A mistake was made.</em></li>
</ul>

<p><strong>Ukrainian:</strong> Пасивний стан — будинок був збудований. (будується / збудований)</p>
<p><strong>Greek:</strong> Παθητική φωνή — Το βιβλίο γράφτηκε από τον συγγραφέα.</p>

<hr/>
<h2>Reported Speech</h2>
<p>Reported speech (indirect speech) conveys what someone said without quoting them directly. Tenses and pronouns usually shift.</p>

<h3>Tense Shifts in Reported Speech</h3>
<table class="table table-bordered table-sm">
<thead class="table-dark"><tr><th>Direct Speech Tense</th><th>Reported Speech Tense</th></tr></thead>
<tbody>
<tr><td>Present Simple: "I work"</td><td>Past Simple: he said he worked</td></tr>
<tr><td>Present Continuous: "I am working"</td><td>Past Continuous: he said he was working</td></tr>
<tr><td>Past Simple: "I worked"</td><td>Past Perfect: he said he had worked</td></tr>
<tr><td>Present Perfect: "I have worked"</td><td>Past Perfect: he said he had worked</td></tr>
<tr><td>Will: "I will come"</td><td>Would: he said he would come</td></tr>
<tr><td>Can: "I can help"</td><td>Could: he said he could help</td></tr>
</tbody>
</table>

<h3>Other Changes in Reported Speech</h3>
<table class="table table-bordered table-sm">
<thead><tr><th>Direct</th><th>Reported</th></tr></thead>
<tbody>
<tr><td>today</td><td>that day</td></tr>
<tr><td>yesterday</td><td>the day before</td></tr>
<tr><td>tomorrow</td><td>the next day / the following day</td></tr>
<tr><td>here</td><td>there</td></tr>
<tr><td>this</td><td>that</td></tr>
<tr><td>now</td><td>then</td></tr>
</tbody>
</table>

<h3>Reporting Verbs</h3>
<p>Instead of only <em>say/tell</em>, use precise reporting verbs:</p>
<ul>
<li><strong>admit</strong> — He admitted that he was wrong.</li>
<li><strong>deny</strong> — She denied taking the money.</li>
<li><strong>suggest</strong> — He suggested going to the cinema.</li>
<li><strong>promise</strong> — She promised to call.</li>
<li><strong>warn</strong> — He warned me not to touch it.</li>
<li><strong>ask/request</strong> — She asked me to help her.</li>
</ul>

<p><strong>Ukrainian:</strong> Непряма мова — Він сказав, що він працює. / Вона запитала, чи можу я допомогти.</p>
''',
        },
    ]

    for s in sections:
        if not GS.search([('slug', '=', s['slug'])], limit=1):
            GS.create(s)


def post_init_hook(env):
    _seed_knowledge_hub(env)


def post_update_hook(env):
    _seed_knowledge_hub(env)
