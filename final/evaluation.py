# evaluation.py
# validation experiments for report
# combines user ratings with automated metrics for results

import pandas as pd
import numpy as np
import random
import time
from datetime import datetime

# import our modules
from ga_planner import run_genetic_algorithm, calculate_fitness
from heuristic_planner import run_heuristic_search
from spacy_parser import parse_with_spacy
from nlp_classifier import get_keyword_vibes

# rating scale for planners
RATING_SCALE = {
    1: 'Very Bad',
    2: 'Bad',
    3: 'Okay',
    4: 'Happy',
    5: 'Very Happy'
}


def random_baseline(df, num_stops, budget):
    # random planner baseline - just picks random venues to compare against
    venues = df[df['cost'] <= budget].to_dict('records')
    if len(venues) < num_stops:
        return venues[:num_stops] if venues else []
    return random.sample(venues, num_stops)


def compute_plan_metrics(plan, budget, target_vibes, target_types):
    # computes automated metrics for a plan using the GA fitness function
    if not plan:
        return {'budget_ok': False, 'cost': 0, 'diversity': 0, 'vibe_match': 0, 'avg_rating': 0, 'fitness': 0}

    total_cost = sum(p.get('cost', 0) for p in plan)

    # use the actual fitness function from GA
    fitness = calculate_fitness(plan, budget, target_types=target_types, target_vibes=target_vibes)

    # type diversity (% unique)
    types = [p.get('type', '') for p in plan]
    diversity = len(set(types)) / len(types) * 100 if types else 0

    # vibe match rate
    vibe_matches = 0
    for p in plan:
        p_vibes = [v.strip().lower() for v in str(p.get('true_vibe', '')).split(',')]
        if any(tv.lower() in p_vibes for tv in target_vibes):
            vibe_matches += 1
    vibe_match = vibe_matches / len(plan) * 100 if plan else 0

    # avg rating
    ratings = [p.get('rating', 0) for p in plan]
    avg_rating = np.mean(ratings) if ratings else 0

    return {
        'budget_ok': total_cost <= budget,
        'cost': total_cost,
        'diversity': diversity,
        'vibe_match': vibe_match,
        'avg_rating': avg_rating,
        'fitness': fitness  # actual GA fitness score
    }


# test 1 - compare random vs heuristic vs GA
def test_planner_accuracy(csv_path='ottawa_venues.csv'):
    print("\n" + "=" * 70)
    print("TEST 1: PLANNER COMPARISON (Random vs Heuristic vs GA)")
    print("=" * 70)
    print("\nRate each plan based on OVERALL DATE QUALITY:")
    print("  - Does it feel like a good date?")
    print("  - Does it match the requested vibe?")
    print("  - Is there good variety (not all same type)?")
    print("  - Would you actually do this date?")
    print("\n1=Very Bad, 2=Bad, 3=Okay, 4=Happy, 5=Very Happy")
    print("=" * 70)

    df = pd.read_csv(csv_path)

    # 15 test scenarios
    queries = [
        {'vibes': ['romantic'], 'types': ['italian'], 'budget': 100, 'stops': 3, 'desc': 'Romantic Italian dinner'},
        {'vibes': ['energetic'], 'types': ['bar'], 'budget': 80, 'stops': 3, 'desc': 'Night out at bars'},
        {'vibes': ['cozy'], 'types': ['coffee'], 'budget': 50, 'stops': 2, 'desc': 'Cozy coffee date'},
        {'vibes': ['fancy'], 'types': ['french'], 'budget': 150, 'stops': 3, 'desc': 'Fancy French dinner'},
        {'vibes': ['casual'], 'types': ['pizza'], 'budget': 40, 'stops': 2, 'desc': 'Casual pizza night'},
        {'vibes': ['hipster'], 'types': ['cafe'], 'budget': 60, 'stops': 3, 'desc': 'Hipster cafe crawl'},
        {'vibes': ['family'], 'types': ['restaurant'], 'budget': 120, 'stops': 3, 'desc': 'Family dinner outing'},
        {'vibes': ['romantic', 'cozy'], 'types': ['wine'], 'budget': 100, 'stops': 2, 'desc': 'Romantic wine evening'},
        {'vibes': ['energetic'], 'types': ['pub'], 'budget': 70, 'stops': 3, 'desc': 'Pub crawl'},
        {'vibes': ['foodie'], 'types': ['sushi'], 'budget': 90, 'stops': 2, 'desc': 'Sushi foodie date'},
        {'vibes': ['casual'], 'types': ['brunch'], 'budget': 50, 'stops': 2, 'desc': 'Casual brunch'},
        {'vibes': ['romantic'], 'types': ['steakhouse'], 'budget': 130, 'stops': 2, 'desc': 'Romantic steakhouse'},
        {'vibes': ['cozy'], 'types': ['bakery'], 'budget': 30, 'stops': 2, 'desc': 'Cozy bakery visit'},
        {'vibes': ['energetic', 'casual'], 'types': ['mexican'], 'budget': 60, 'stops': 3, 'desc': 'Fun Mexican night'},
        {'vibes': ['hipster'], 'types': ['cocktail'], 'budget': 80, 'stops': 2, 'desc': 'Hipster cocktail bars'},
    ]

    # store both ratings and metrics
    results = {
        'Random': {'ratings': [], 'metrics': []},
        'Heuristic': {'ratings': [], 'metrics': []},
        'GA': {'ratings': [], 'metrics': [], 'times': []}
    }

    for q in queries:
        print(f"\n{'='*60}")
        print(f"Query: {q['desc']} (${q['budget']}, {q['stops']} stops)")
        print(f"{'='*60}")

        # RANDOM baseline
        plan_r = random_baseline(df.copy(), q['stops'], q['budget'])
        metrics_r = compute_plan_metrics(plan_r, q['budget'], q['vibes'], q['types'])
        print("\n[RANDOM Baseline]")
        for i, p in enumerate(plan_r, 1):
            print(f"  {i}. {p['name'][:35]:<35} | ${p['cost']:<4} | {p.get('true_vibe', '?')[:15]}")
        print(f"  -> Budget OK: {metrics_r['budget_ok']}, Diversity: {metrics_r['diversity']:.0f}%, Vibe Match: {metrics_r['vibe_match']:.0f}%")
        rating_r = input("Rate Random (1-5): ").strip()
        results['Random']['ratings'].append(int(rating_r) if rating_r.isdigit() else 3)
        results['Random']['metrics'].append(metrics_r)

        # HEURISTIC
        t0 = time.time()
        plan_h = run_heuristic_search(df.copy(), q['vibes'], q['budget'], q['stops'], target_types=q['types'])
        time_h = time.time() - t0
        metrics_h = compute_plan_metrics(plan_h, q['budget'], q['vibes'], q['types'])
        print("\n[HEURISTIC]")
        for i, p in enumerate(plan_h, 1):
            print(f"  {i}. {p['name'][:35]:<35} | ${p['cost']:<4} | {p.get('true_vibe', '?')[:15]}")
        print(f"  -> Budget OK: {metrics_h['budget_ok']}, Diversity: {metrics_h['diversity']:.0f}%, Vibe Match: {metrics_h['vibe_match']:.0f}%")
        rating_h = input("Rate Heuristic (1-5): ").strip()
        results['Heuristic']['ratings'].append(int(rating_h) if rating_h.isdigit() else 3)
        results['Heuristic']['metrics'].append(metrics_h)

        # GA
        t0 = time.time()
        plan_g = run_genetic_algorithm(df.copy(), q['vibes'], q['budget'], q['stops'], target_types=q['types'])
        time_g = time.time() - t0
        metrics_g = compute_plan_metrics(plan_g, q['budget'], q['vibes'], q['types'])
        print("\n[GENETIC ALGORITHM]")
        for i, p in enumerate(plan_g, 1):
            print(f"  {i}. {p['name'][:35]:<35} | ${p['cost']:<4} | {p.get('true_vibe', '?')[:15]}")
        print(f"  -> Budget OK: {metrics_g['budget_ok']}, Diversity: {metrics_g['diversity']:.0f}%, Vibe Match: {metrics_g['vibe_match']:.0f}%, Time: {time_g:.2f}s")
        rating_g = input("Rate GA (1-5): ").strip()
        results['GA']['ratings'].append(int(rating_g) if rating_g.isdigit() else 3)
        results['GA']['metrics'].append(metrics_g)
        results['GA']['times'].append(time_g)

    # results
    print("\n" + "=" * 70)
    print("RESULTS - PLANNER COMPARISON")
    print("=" * 70)

    # Table 1: User Satisfaction Ratings
    print("\nTable 1: User Satisfaction Ratings (1-5 scale)")
    print("-" * 50)
    print(f"{'Method':<12} {'Mean':<8} {'Std':<8} {'Min':<6} {'Max':<6} {'Satisfaction'}")
    print("-" * 50)
    for method in ['Random', 'Heuristic', 'GA']:
        ratings = results[method]['ratings']
        mean = np.mean(ratings)
        std = np.std(ratings)
        print(f"{method:<12} {mean:<8.2f} {std:<8.2f} {min(ratings):<6} {max(ratings):<6} {RATING_SCALE.get(round(mean), 'Okay')}")

    # Table 2: Automated Metrics (includes GA fitness score)
    print("\nTable 2: Automated Performance Metrics")
    print("-" * 85)
    print(f"{'Method':<12} {'Budget Pass%':<14} {'Diversity%':<12} {'Vibe Match%':<12} {'Avg Rating':<12} {'Fitness'}")
    print("-" * 85)
    for method in ['Random', 'Heuristic', 'GA']:
        metrics = results[method]['metrics']
        budget_pass = sum(1 for m in metrics if m['budget_ok']) / len(metrics) * 100
        diversity = np.mean([m['diversity'] for m in metrics])
        vibe_match = np.mean([m['vibe_match'] for m in metrics])
        avg_rating = np.mean([m['avg_rating'] for m in metrics])
        fitness = np.mean([m['fitness'] for m in metrics])
        print(f"{method:<12} {budget_pass:<14.1f} {diversity:<12.1f} {vibe_match:<12.1f} {avg_rating:<12.2f} {fitness:.1f}")

    # Table 3: GA Convergence
    print("\nTable 3: GA Convergence Speed")
    print("-" * 40)
    times = results['GA']['times']
    print(f"Mean time: {np.mean(times):.2f}s")
    print(f"Std dev:   {np.std(times):.2f}s")
    print(f"Min time:  {min(times):.2f}s")
    print(f"Max time:  {max(times):.2f}s")

    return results


# test 2 - nlp parsing accuracy
def test_nlp_parsing():
    print("\n" + "=" * 60)
    print("TEST 2: NLP QUERY PARSING ACCURACY")
    print("Check each extracted field: vibes, types, budget, stops")
    print("=" * 60)

    # 20 test queries with expected outputs for comparison
    test_queries = [
        {"query": "I want a romantic italian dinner for $100 in Ottawa", "expect": "vibes:romantic, types:italian, budget:100"},
        {"query": "Find me 3 cozy coffee shops under $50", "expect": "vibes:cozy, types:coffee, budget:50, stops:3"},
        {"query": "energetic night out with bars and clubs, budget $80", "expect": "vibes:energetic, types:bar/club, budget:80"},
        {"query": "fancy french restaurant for anniversary, willing to spend $150", "expect": "vibes:fancy, types:french, budget:150"},
        {"query": "casual brunch spots, hipster vibe, around $40", "expect": "vibes:casual/hipster, types:brunch, budget:40"},
        {"query": "looking for a fun date with pizza and bowling", "expect": "vibes:fun, types:pizza/bowling"},
        {"query": "romantic evening with wine and good food for $120", "expect": "vibes:romantic, types:wine, budget:120"},
        {"query": "2 stops, casual pub crawl, budget $60", "expect": "vibes:casual, types:pub, budget:60, stops:2"},
        {"query": "cozy bakery and cafe date, $30 max", "expect": "vibes:cozy, types:bakery/cafe, budget:30"},
        {"query": "find me hipster cocktail bars in ottawa", "expect": "vibes:hipster, types:cocktail/bar"},
        {"query": "family friendly restaurants under $100", "expect": "vibes:family, types:restaurant, budget:100"},
        {"query": "energetic mexican food night, 3 stops", "expect": "vibes:energetic, types:mexican, stops:3"},
        {"query": "fancy steakhouse dinner for two, $150 budget", "expect": "vibes:fancy, types:steakhouse, budget:150"},
        {"query": "sushi date, foodie vibe, around $80", "expect": "vibes:foodie, types:sushi, budget:80"},
        {"query": "late night tacos and drinks, casual, $50", "expect": "vibes:casual, types:tacos, budget:50"},
        {"query": "romantic french bistro for $100", "expect": "vibes:romantic, types:french/bistro, budget:100"},
        {"query": "4 stops coffee and dessert crawl, cozy, $40", "expect": "vibes:cozy, types:coffee/dessert, budget:40, stops:4"},
        {"query": "upscale dining experience, $200 budget", "expect": "vibes:upscale/fancy, budget:200"},
        {"query": "casual greek food, family vibe, $70", "expect": "vibes:casual/family, types:greek, budget:70"},
        {"query": "hipster brunch spots in the market area", "expect": "vibes:hipster, types:brunch"},
    ]

    # track individual field accuracy
    field_correct = {'vibes': 0, 'types': 0, 'budget': 0, 'stops': 0}
    overall_correct = 0
    total = len(test_queries)

    for item in test_queries:
        query = item['query']
        expected = item['expect']

        print(f"\n{'='*60}")
        print(f"Query: \"{query}\"")
        print(f"Expected: {expected}")

        result = parse_with_spacy(query)

        print(f"\nExtracted:")
        print(f"  Vibes:    {result.get('target_vibes', [])}")
        print(f"  Types:    {result.get('target_types', [])}")
        print(f"  Budget:   ${result.get('budget_limit', 'not found')}")
        print(f"  Stops:    {result.get('itinerary_length', 'not found')}")
        print(f"  Location: {result.get('location', 'not found')}")

        # rate each field
        print("\nRate each field (y=correct, n=wrong, s=skip):")

        v = input("  Vibes correct? (y/n/s): ").strip().lower()
        if v == 'y': field_correct['vibes'] += 1

        t = input("  Types correct? (y/n/s): ").strip().lower()
        if t == 'y': field_correct['types'] += 1

        b = input("  Budget correct? (y/n/s): ").strip().lower()
        if b == 'y': field_correct['budget'] += 1

        st = input("  Stops correct? (y/n/s): ").strip().lower()
        if st == 'y': field_correct['stops'] += 1

        overall = input("  Overall correct? (y/n): ").strip().lower()
        if overall == 'y': overall_correct += 1

    print("\n" + "=" * 60)
    print("RESULTS - NLP PARSING")
    print("=" * 60)

    print("\nTable: Field-Level Accuracy")
    print("-" * 40)
    print(f"{'Field':<12} {'Correct':<10} {'Total':<10} {'Accuracy'}")
    print("-" * 40)
    for field, correct in field_correct.items():
        acc = correct / total * 100
        print(f"{field:<12} {correct:<10} {total:<10} {acc:.1f}%")

    print("-" * 40)
    overall_acc = overall_correct / total * 100
    print(f"{'OVERALL':<12} {overall_correct:<10} {total:<10} {overall_acc:.1f}%")

    return {
        'field_accuracy': field_correct,
        'overall_correct': overall_correct,
        'total': total,
        'overall_accuracy': overall_acc
    }


# test 3 - vibe classification accuracy
def test_vibe_classification(csv_path='ottawa_venues.csv'):
    print("\n" + "=" * 60)
    print("TEST 3: VENUE VIBE CLASSIFICATION ACCURACY")
    print("Read the venue info, then rate if the predicted vibe is correct")
    print("=" * 60)

    df = pd.read_csv(csv_path)
    df = df.dropna(subset=['description'])

    # sample 20 random venues
    sample = df.sample(min(20, len(df)), random_state=42)

    # track by vibe category
    results_by_vibe = {}
    correct = 0
    total = len(sample)

    for idx, (_, row) in enumerate(sample.iterrows(), 1):
        print(f"\n{'='*60}")
        print(f"Venue {idx}/{total}: {row['name']}")
        print(f"{'='*60}")
        print(f"Type: {row.get('type', row.get('primary_type_display_name', '?'))}")
        print(f"Rating: {row.get('rating', '?')} stars")

        desc = str(row.get('description', ''))
        review = str(row.get('review', ''))
        print(f"\nDescription:")
        print(f"  {desc[:200]}...")

        if pd.notna(row.get('review')):
            print(f"\nReview snippet:")
            print(f"  {review[:150]}...")

        # use get_keyword_vibes to show what classifier extracts
        # IMPORTANT: pass venue_type to get type-based vibe inference
        combined_text = desc + ' ' + review
        venue_type = row.get('type', '')
        live_vibes = get_keyword_vibes(combined_text, venue_type=venue_type)
        stored_vibe = row.get('true_vibe', 'unknown')

        print(f"\n>> Stored Vibe: {stored_vibe}")
        print(f">> Live keyword extraction: {live_vibes if live_vibes else 'none detected'}")

        # track by vibe
        primary_vibe = stored_vibe.split(',')[0].strip() if stored_vibe else 'unknown'
        if primary_vibe not in results_by_vibe:
            results_by_vibe[primary_vibe] = {'correct': 0, 'total': 0}
        results_by_vibe[primary_vibe]['total'] += 1

        is_correct = input("\nIs this vibe correct? (y/n): ").strip().lower()
        if is_correct == 'y':
            correct += 1
            results_by_vibe[primary_vibe]['correct'] += 1

    print("\n" + "=" * 60)
    print("RESULTS - VIBE CLASSIFICATION")
    print("=" * 60)

    overall_acc = correct / total * 100
    print(f"\nOverall Accuracy: {correct}/{total} = {overall_acc:.1f}%")

    print("\nTable: Accuracy by Vibe Category")
    print("-" * 50)
    print(f"{'Vibe':<15} {'Correct':<10} {'Total':<10} {'Accuracy'}")
    print("-" * 50)
    for vibe, data in sorted(results_by_vibe.items()):
        acc = data['correct'] / data['total'] * 100 if data['total'] > 0 else 0
        print(f"{vibe:<15} {data['correct']:<10} {data['total']:<10} {acc:.1f}%")

    return {
        'correct': correct,
        'total': total,
        'accuracy': overall_acc,
        'by_vibe': results_by_vibe
    }


def save_results_to_file(results, filename='evaluation_results.txt'):
    # saves all results to a text file so we can include it in the report
    with open(filename, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("OTTAWA DATE PLANNER - EVALUATION RESULTS\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 70 + "\n\n")

        if 'planner' in results:
            f.write("PLANNER COMPARISON RESULTS\n")
            f.write("-" * 50 + "\n\n")

            f.write("Table 1: User Satisfaction Ratings (1-5 scale)\n")
            f.write(f"{'Method':<12} {'Mean':<8} {'Std':<8} {'Min':<6} {'Max':<6}\n")
            f.write("-" * 40 + "\n")
            for method in ['Random', 'Heuristic', 'GA']:
                ratings = results['planner'][method]['ratings']
                mean = np.mean(ratings)
                std = np.std(ratings)
                f.write(f"{method:<12} {mean:<8.2f} {std:<8.2f} {min(ratings):<6} {max(ratings):<6}\n")

            f.write("\nTable 2: Automated Performance Metrics\n")
            f.write(f"{'Method':<12} {'Budget%':<10} {'Diversity%':<12} {'Vibe%':<10} {'Fitness'}\n")
            f.write("-" * 55 + "\n")
            for method in ['Random', 'Heuristic', 'GA']:
                metrics = results['planner'][method]['metrics']
                budget_pass = sum(1 for m in metrics if m['budget_ok']) / len(metrics) * 100
                diversity = np.mean([m['diversity'] for m in metrics])
                vibe_match = np.mean([m['vibe_match'] for m in metrics])
                fitness = np.mean([m['fitness'] for m in metrics])
                f.write(f"{method:<12} {budget_pass:<10.1f} {diversity:<12.1f} {vibe_match:<10.1f} {fitness:.1f}\n")

            if 'times' in results['planner']['GA']:
                times = results['planner']['GA']['times']
                f.write(f"\nGA Convergence: Mean={np.mean(times):.2f}s, Std={np.std(times):.2f}s\n")
            f.write("\n")

        if 'nlp' in results:
            f.write("NLP QUERY PARSING RESULTS\n")
            f.write("-" * 50 + "\n")
            f.write(f"Overall Accuracy: {results['nlp']['overall_accuracy']:.1f}%\n")
            f.write("\nField-Level Accuracy:\n")
            for field, count in results['nlp']['field_accuracy'].items():
                acc = count / results['nlp']['total'] * 100
                f.write(f"  {field}: {acc:.1f}%\n")
            f.write("\n")

        if 'vibe' in results:
            f.write("VENUE VIBE CLASSIFICATION RESULTS\n")
            f.write("-" * 50 + "\n")
            f.write(f"Overall Accuracy: {results['vibe']['accuracy']:.1f}%\n")
            f.write("\n")

    print(f"\nResults saved to {filename}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("OTTAWA DATE PLANNER - VALIDATION EXPERIMENTS")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("\nThis is interactive - you rate/verify outputs, then it calculates accuracy.\n")

    print("Which test do you want to run?")
    print("  1. Planner Comparison (Random vs Heuristic vs GA - 15 scenarios)")
    print("  2. NLP Query Parsing (20 test queries)")
    print("  3. Venue Vibe Classification (20 venues)")
    print("  4. Run All Tests")

    choice = input("\nEnter choice (1-4): ").strip()

    results = {}

    if choice == '1' or choice == '4':
        results['planner'] = test_planner_accuracy()

    if choice == '2' or choice == '4':
        results['nlp'] = test_nlp_parsing()

    if choice == '3' or choice == '4':
        results['vibe'] = test_vibe_classification()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if 'planner' in results:
        print("\n[PLANNER COMPARISON]")
        for method in ['Random', 'Heuristic', 'GA']:
            ratings = results['planner'][method]['ratings']
            metrics = results['planner'][method]['metrics']
            avg_rating = np.mean(ratings)
            vibe_match = np.mean([m['vibe_match'] for m in metrics])
            diversity = np.mean([m['diversity'] for m in metrics])
            print(f"  {method}: {avg_rating:.2f}/5 satisfaction, {vibe_match:.1f}% vibe match, {diversity:.1f}% diversity")

        if 'times' in results['planner']['GA']:
            print(f"  GA avg convergence time: {np.mean(results['planner']['GA']['times']):.2f}s")

    if 'nlp' in results:
        print("\n[NLP QUERY PARSING]")
        print(f"  Overall Accuracy: {results['nlp']['overall_accuracy']:.1f}%")
        for field, count in results['nlp']['field_accuracy'].items():
            acc = count / results['nlp']['total'] * 100
            print(f"  {field}: {acc:.1f}%")

    if 'vibe' in results:
        print("\n[VENUE VIBE CLASSIFICATION]")
        print(f"  Overall Accuracy: {results['vibe']['accuracy']:.1f}%")

    print("\n" + "=" * 70)
    print("Copy the tables above into your report!")
    print("=" * 70)

    # save results to file
    save_results_to_file(results)

