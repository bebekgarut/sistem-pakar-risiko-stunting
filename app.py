from flask import Flask, request, render_template, redirect, url_for, session
import csv

app = Flask(__name__)
app.secret_key = 'dhsssssdg42233qr36436ssgf'

def load_rules_from(filepath):
    rules = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rules.append(row)
    return rules

def cocok(fakta_user, premis, nilai):
    nilai_user = fakta_user.get(premis)
    if not nilai_user:
        return None 
    if nilai.startswith('<'):
        return float(nilai_user) < float(nilai[1:])
    elif nilai.startswith('>'):
        return float(nilai_user) > float(nilai[1:])
    elif '-' in nilai:
        low, high = nilai.split('-')
        return float(low) <= float(nilai_user) <= float(high)
    else:
        return nilai_user.lower() == nilai.lower()
    
def evaluasi_faktor(fakta, rules, premis_list, hasil_key):
    for rule in rules:
        cocok_semua = True
        cf_premis_list = []

        for premis in premis_list:
            if rule[premis] == '-':
                continue

            if premis in fakta:
                nilai_pengguna = fakta[premis]['nilai']
                if nilai_pengguna == '':
                    return None, premis

                if cocok({premis: nilai_pengguna}, premis, rule[premis]):
                    cf_premis = float(fakta[premis].get('cf', 1))
                    cf_premis_list.append(cf_premis)
                else:
                    cocok_semua = False
                    break
            else:
                return None, premis

        if cocok_semua:
            cf_rule = float(rule.get('cf', 1))
            cf_kesimpulan = min(cf_premis_list) * cf_rule
            print(cf_kesimpulan)
            fakta[hasil_key] = {'nilai': rule[hasil_key], 'cf': cf_kesimpulan}
            return rule[hasil_key], None

    return None, None

@app.route('/', methods=['GET', 'POST'])
def index():
    session.setdefault('fakta', {})
    fakta = session['fakta']

    print(f"Session fakta: {fakta}") 

    if request.method == 'POST':
        if 'init' in request.form:
            for key in request.form:
                if key not in ['init'] and not key.startswith('cf_'):
                    nilai = request.form.get(key, '').strip()
                    if nilai == '': 
                        continue 
                    cf = float(request.form.get(f'cf_{key}', 1.0))
                    session['fakta'][key] = {'nilai': nilai, 'cf': cf}
            session['init_done'] = True
            session.modified = True
            return redirect(url_for('index'))

        else:
            premis = request.form.get('premis')
            nilai = request.form.get('nilai').strip() 
            if nilai == '': 
                return render_template('index.jinja', fakta=fakta, pertanyaan=premis, error="Input tidak boleh kosong.")
            cf = float(request.form['cf'])
            session['fakta'][premis] = {'nilai': nilai, 'cf': cf}
            session.modified = True
            return redirect(url_for('index'))


    if not session.get('init_done'):
        print("Form inisialisasi belum selesai") 
        return render_template('index.jinja', fakta=fakta, pertanyaan=None, init_form=True)

    rules_ibu = load_rules_from('./database/faktor_ibu.csv')
    rules_lingkungan = load_rules_from('./database/faktor_lingkungan.csv')
    rules_pemeriksaan = load_rules_from('./database/faktor_pemeriksaan.csv')
    rules_perencanaan = load_rules_from('./database/faktor_perencanaan.csv')
    rules_risiko = load_rules_from('./database/risiko_stunting.csv')

    faktor_ibu, tanya1 = evaluasi_faktor(fakta, rules_ibu,
        ['usia_ibu', 'imt', 'riwayat_penyakit', 'konsumsi_makanan', 'ketidakstabilan_mental'], 'faktor_ibu')
    if tanya1: return render_template('index.jinja', fakta=fakta, pertanyaan=tanya1)

    faktor_lingkungan, tanya2 = evaluasi_faktor(fakta, rules_lingkungan,
        ['terpapar', 'sanitasi', 'kualitas_air'], 'faktor_lingkungan')
    if tanya2: return render_template('index.jinja', fakta=fakta, pertanyaan=tanya2)

    faktor_pemeriksaan, tanya3 = evaluasi_faktor(fakta, rules_pemeriksaan,
        ['usia_kehamilan', 'frekuensi_pemeriksaan', 'konsumsi_suplemen'], 'faktor_pemeriksaan')
    if tanya3: return render_template('index.jinja', fakta=fakta, pertanyaan=tanya3)

    faktor_perencanaan, tanya4 = evaluasi_faktor(fakta, rules_perencanaan,
        ['jarak_kehamilan', 'pemakaian_kb'], 'faktor_perencanaan')
    if tanya4: return render_template('index.jinja', fakta=fakta, pertanyaan=tanya4)

    fakta_risiko = {
        'faktor_ibu': faktor_ibu,
        'faktor_lingkungan': faktor_lingkungan,
        'faktor_pemeriksaan': faktor_pemeriksaan,
        'faktor_perencanaan': faktor_perencanaan,
    }
    
    print(fakta_risiko)

    risiko = None
    for rule in rules_risiko:
        cocok_semua = True
        for k in fakta_risiko:
            if rule[k] == '-':
                continue
            if rule[k].lower() != fakta_risiko[k].lower():
                print(rule[k])
                cocok_semua = False
                break
        if cocok_semua:
            risiko = rule['risiko_stunting']
            break

    print(risiko)
    return render_template('hasil.jinja',
        faktor_ibu=faktor_ibu,
        faktor_lingkungan=faktor_lingkungan,
        faktor_pemeriksaan=faktor_pemeriksaan,
        faktor_perencanaan=faktor_perencanaan,
        risiko=risiko,
        fakta=fakta
    )

@app.route('/reset')
def reset():
    session.pop('fakta', None)
    session.pop('init_done', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
